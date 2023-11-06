import sqlite3
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import structlog

from metrics.github.prs import process_prs
from metrics.logs import setup_logging
from metrics.timescaledb import TimescaleDBWriter
from metrics.tools.dates import date_from_iso, datetime_from_iso, iter_days


setup_logging()

log = structlog.get_logger()


def get_data(db, orgs):
    subprocess.check_call(["github-to-sqlite", "repos", db, *orgs])

    con = sqlite3.connect(db)
    cur = con.cursor()

    for org in orgs:
        result = cur.execute(
            "SELECT name FROM repos WHERE full_name LIKE ?", (f"{org}%",)
        ).fetchall()
        repo_names = [r[0] for r in result]

        for repo in repo_names:
            subprocess.check_call(
                ["github-to-sqlite", "pull-requests", db, f"{org}/{repo}"]
            )


def get_prs():
    sql = """
    SELECT
      date(pull_requests.created_at) as created,
      date(pull_requests.closed_at) as closed,
      authors.login as author,
      repos.name as repo,
      owners.login as org
    FROM
      pull_requests
      LEFT OUTER JOIN repos ON (pull_requests.repo = repos.id)
      LEFT OUTER JOIN users owners ON (repos.owner = owners.id)
      LEFT OUTER JOIN users authors ON (pull_requests.user = authors.id)
    WHERE
      draft = 0
    """
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    return list(cur.execute(sql))


def pr_queue(prs, org, start, days_threshold=None):
    dates = iter_days(start, date.today(), step=timedelta(days=1))
    for day in dates:
        prs_on_day = [
            pr
            for pr in prs
            if date_from_iso(pr["created"]) <= day
            and date_from_iso(pr["closed"]) >= day
        ]

        if days_threshold is not None:
            # remove PRs which have been open <days_threshold days
            prs_on_day = [
                pr
                for pr in prs_on_day
                if (date_from_iso(pr["closed"]) - date_from_iso(pr["created"]))
                >= timedelta(days=days_threshold)
            ]

        suffix = f"_older_than_{days_threshold}_days" if days_threshold else ""
        key = f"queue{suffix}"

        log.info("%s | %s | %s | Processing %s PRs", key, day, org, len(prs_on_day))
        with TimescaleDBWriter("github_pull_requests", f"queue{suffix}") as writer:
            process_prs(writer, prs_on_day, day)


def pr_throughput(prs, org, start):
    # get the previous DoW that we care about
    # loop through dates invoking the CLI entrypoint for each date
    def next_weekday(d, weekday):
        # 0 = Monday, 1=Tuesday, 2=Wednesday...
        days_ahead = weekday - d.weekday()

        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7

        return d + timedelta(days=days_ahead)

    first_sunday = next_weekday(start - timedelta(days=7), 7)
    next_sunday = next_weekday(date.today(), 7)
    dates = [
        first_sunday,
        *list(iter_days(start, date.today(), step=timedelta(days=7))),
        next_sunday,
    ]

    for day in dates:
        start = day - timedelta(days=7)
        end = day

        prs_in_range = [
            pr
            for pr in prs
            if date_from_iso(pr["created"]) >= start
            and date_from_iso(pr["created"]) <= end
        ]

        key = "throughput"
        log.info("%s | %s | %s | Processing %s PRs", key, day, org, len(prs_in_range))
        with TimescaleDBWriter("github_pull_requests", "throughput") as writer:
            process_prs(writer, prs_in_range, day)


if __name__ == "__main__":
    db = "github.db"
    orgs = ["ebmdatalab", "opensafely-core"]

    # hacky switch for [re-]building the local SQLite
    args = sys.argv[1:]
    if args and args[0] == "--pull-data":
        # clean up existing db
        Path(db).unlink(missing_ok=True)

        # pull all data down to make backfilling quicker
        get_data(db, orgs)

    prs = get_prs()

    for org in orgs:
        org_prs = [pr for pr in prs if pr["org"] == org]
        log.info("Backfilling with %s PRs for %s", len(org_prs), org)
        start_date = min([pr["created"] for pr in org_prs])
        start_date = datetime_from_iso(start_date).date()

        pr_queue(org_prs, org, start_date)

        for day in [2, 10, 30, 60]:
            pr_queue(org_prs, org, start_date, days_threshold=day)

        pr_throughput(org_prs, org, start_date)
