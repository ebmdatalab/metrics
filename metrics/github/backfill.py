import sqlite3
import subprocess
from datetime import date, timedelta
from pathlib import Path

import click
import structlog

from ..logs import setup_logging
from ..timescaledb import TimescaleDBWriter
from ..timescaledb.tables import GitHubPullRequests
from ..tools.dates import date_from_iso, iter_days
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


def open_prs(prs, org, start, days_threshold):
    dates = list(iter_days(start, date.today()))

    with TimescaleDBWriter(GitHubPullRequests) as writer:
        for day in dates:
            prs_on_day = [
                pr
                for pr in prs
                if date_from_iso(pr["created"]) <= day
                and date_from_iso(pr["closed"]) >= day
            ]

            # remove PRs which have been open <days_threshold days
            prs_on_day = [
                pr
                for pr in prs_on_day
                if (date_from_iso(pr["closed"]) - date_from_iso(pr["created"]))
                >= timedelta(days=days_threshold)
            ]

            name = f"queue_older_than_{days_threshold}_days"

            log.info(
                "%s | %s | %s | Processing %s PRs", name, day, org, len(prs_on_day)
            )
            process_prs(writer, prs_on_day, day, name=name)


def pr_throughput(prs, org, start):
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
    start_date = date_from_iso(min([pr["created"] for pr in org_prs]))

    for day in [2, 7, 10, 30, 60]:
        open_prs(org_prs, org, start_date, days_threshold=day)

    pr_throughput(org_prs, org, start_date)
