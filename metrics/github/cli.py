from datetime import date, timedelta

import click
import structlog
from sqlalchemy import create_engine

from ..timescaledb import TimescaleDBWriter, drop_tables
from ..timescaledb.tables import GitHubPullRequests
from ..timescaledb.writer import TIMESCALEDB_URL
from ..tools.dates import iter_days, previous_weekday
from . import api
from .prs import process_prs


log = structlog.get_logger()


def open_prs(prs, org, days_threshold):
    earliest = min([pr["created"] for pr in prs])
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
        closed = pr["closed"] or today
        opened = pr["created"]

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
    start = min([pr["created"] for pr in prs])
    days = list(iter_days(start, date.today()))

    with TimescaleDBWriter(GitHubPullRequests) as writer:
        for day in days:
            opened_prs = [pr for pr in prs if pr["created"] == day]
            log.info("%s | %s | Processing %s opened PRs", day, org, len(opened_prs))
            process_prs(writer, opened_prs, day, name="prs_opened")

            merged_prs = [pr for pr in prs if pr["merged"] and pr["merged"] == day]
            log.info("%s | %s | Processing %s merged PRs", day, org, len(merged_prs))
            process_prs(writer, merged_prs, day, name="prs_merged")


@click.command()
@click.option("--token", required=True, envvar="GITHUB_TOKEN")
@click.pass_context
def github(ctx, token):
    ctx.ensure_object(dict)
    ctx.obj["TOKEN"] = token

    log.info("Dropping existing github_* tables")
    # TODO: we have this in two places now, can we pull into some kind of
    # service wrapper?
    engine = create_engine(TIMESCALEDB_URL)
    with engine.begin() as connection:
        drop_tables(connection, prefix="github_")
    log.info("Dropped existing github_* tables")

    orgs = [
        "ebmdatalab",
        "opensafely-core",
    ]
    for org in orgs:
        log.info("Working with org: %s", org)
        prs = list(api.iter_prs(org))
        log.info("Backfilling with %s PRs for %s", len(prs), org)

        open_prs(prs, org, days_threshold=7)
        pr_throughput(prs, org)
