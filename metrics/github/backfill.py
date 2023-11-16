import sqlite3
import subprocess
from datetime import date, timedelta
from pathlib import Path

import click
import structlog

from ..logs import setup_logging
from ..timescaledb import TimescaleDBWriter
from ..timescaledb.tables import GitHubPullRequests
from ..tools.dates import date_from_iso, iter_days, previous_weekday
from .prs import process_prs


setup_logging()

log = structlog.get_logger()


def get_data(db, org):
    subprocess.check_call(["github-to-sqlite", "repos", db, org])

    con = sqlite3.connect(db)
    cur = con.cursor()

    result = cur.execute(
        "SELECT name FROM repos WHERE full_name LIKE ?", (f"{org}%",)
    ).fetchall()
    repo_names = [r[0] for r in result]

    for repo in repo_names:
        subprocess.check_call(
            ["github-to-sqlite", "pull-requests", db, f"{org}/{repo}"]
        )


def get_prs(db):
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


def open_prs(prs, org, days_threshold):
    earliest = date_from_iso(min([pr["created"] for pr in prs]))
    start = previous_weekday(earliest, 0)  # Monday
    mondays = list(iter_days(start, date.today(), step=timedelta(days=7)))

    today = date.today()
    threshold = timedelta(days=days_threshold)

    def open_on_day(pr, start, end):
        """
        Filter function for PRs

        Checks whether a PR is open today and if it's been open for greater or
        equal to the threshold of days.
        """
        closed = date_from_iso(pr["closed"]) or today
        opened = date_from_iso(pr["created"])

        open_today = (opened <= start) and (closed >= end)
        if not open_today:
            return False

        return (closed - opened) >= threshold

    with TimescaleDBWriter(GitHubPullRequests) as writer:
        for start in mondays:
            end = start + timedelta(days=6)
            prs_on_day = [pr for pr in prs if open_on_day(pr, start, end)]

            name = f"queue_older_than_{days_threshold}_days"

            log.info(
                "%s | %s | Processing %s PRs from week starting %s",
                name,
                org,
                len(prs_on_day),
                start,
            )
            process_prs(writer, prs_on_day, start, name=name)


def pr_throughput(prs, org):
    start = date_from_iso(min([pr["created"] for pr in prs]))
    days = list(iter_days(start, date.today()))

    with TimescaleDBWriter(GitHubPullRequests) as writer:
        for day in days:
            opened_prs = [pr for pr in prs if date_from_iso(pr["created"]) == day]
            log.info("%s | %s | Processing %s opened PRs", day, org, len(opened_prs))
            process_prs(writer, opened_prs, day, name="prs_opened")

            closed_prs = [
                pr for pr in prs if pr["closed"] and date_from_iso(pr["closed"]) == day
            ]
            log.info("%s | %s | Processing %s closed PRs", day, org, len(closed_prs))
            process_prs(writer, closed_prs, day, name="prs_closed")


@click.command()
@click.argument("org")
@click.option("--pull-data", is_flag=True, default=False)
@click.option("--db-path", type=str, default="github.db")
@click.pass_context
def backfill(ctx, org, pull_data, db_path):
    """Backfill GitHub data for the given GitHub ORG"""
    if pull_data:
        # clean up existing db
        Path(db_path).unlink(missing_ok=True)

        # pull all data down to make backfilling quicker
        get_data(db_path, org)

    prs = get_prs(db_path)

    org_prs = [pr for pr in prs if pr["org"] == org]
    log.info("Backfilling with %s PRs for %s", len(org_prs), org)

    open_prs(org_prs, org, days_threshold=7)
    pr_throughput(org_prs, org)
