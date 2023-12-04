from datetime import UTC, date, datetime, time, timedelta

import click
import structlog
from sqlalchemy import create_engine

from ..timescaledb import TimescaleDBWriter, drop_tables
from ..timescaledb.tables import GitHubPullRequests
from ..timescaledb.writer import TIMESCALEDB_URL
from ..tools.dates import iter_days, previous_weekday
from . import api
from .prs import drop_archived_prs, process_prs


log = structlog.get_logger()


def old_prs(prs, org, days_threshold):
    """
    How many PRs had been open for the given days threshold at a given sample
    point?

    We're using Monday morning here to match how the values in throughput are
    bucketed with timeseriesdb's time_bucket() function

    So we start with the Monday before the earliest PR, then iterate from that
    Monday to todays date, filtering the list of PRs down to just those open on
    the given Monday morning.
    """
    earliest = min([pr["created"] for pr in prs])
    start = previous_weekday(earliest, 0)  # Monday
    mondays = list(iter_days(start, date.today(), step=timedelta(days=7)))

    the_future = datetime(9999, 1, 1, tzinfo=UTC)
    threshold = timedelta(days=days_threshold)

    def is_open(pr, dt):
        """
        Filter function for PRs

        Checks whether a PR was open at the given datetime, and if it has been
        open long enough.
        """
        closed = pr["closed_at"] or the_future
        opened = pr["created_at"]

        open_now = opened < dt < closed
        if not open_now:
            return False

        return (closed - opened) >= threshold

    with TimescaleDBWriter(GitHubPullRequests) as writer:
        for monday in mondays:
            dt = datetime.combine(monday, time(), tzinfo=UTC)
            prs_open = [pr for pr in prs if is_open(pr, dt)]
            prs_open = drop_archived_prs(prs_open, monday)

            name = f"queue_older_than_{days_threshold}_days"

            log.info(
                "%s | %s | Processing %s PRs open at %s",
                name,
                org,
                len(prs_open),
                dt,
            )
            process_prs(writer, prs_open, monday, name=name)


def pr_throughput(prs, org):
    """
    PRs closed each day from the earliest day to today
    """
    start = min([pr["created"] for pr in prs])
    days = list(iter_days(start, date.today()))

    with TimescaleDBWriter(GitHubPullRequests) as writer:
        for day in days:
            valid_prs = drop_archived_prs(prs, day)

            merged_prs = [
                pr for pr in valid_prs if pr["merged"] and pr["merged"] == day
            ]
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

        old_prs(prs, org, days_threshold=7)
        pr_throughput(prs, org)
