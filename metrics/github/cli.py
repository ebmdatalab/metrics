import itertools
import os
from datetime import UTC, date, datetime, time, timedelta

import click
import structlog

from .. import timescaledb
from ..tools.dates import iter_days, previous_weekday
from . import api
from .prs import drop_archived_prs, iter_prs


log = structlog.get_logger()


def old_prs(prs, org, days_threshold):
    """
    Track "old" PRs

    Defined as: How many PRs had been open for the given days threshold at a
    given sample point?

    We're using Monday morning here to match how the values in throughput are
    bucketed with timeseriesdb's time_bucket() function

    So we start with the Monday before the earliest PR, then iterate from that
    Monday to todays date, filtering the list of PRs down to just those open on
    the given Monday morning.
    """
    earliest = min([pr["created_at"] for pr in prs]).date()
    start = previous_weekday(earliest, 0)  # Monday
    mondays = list(iter_days(start, date.today(), step=timedelta(days=7)))

    the_future = datetime(9999, 1, 1, tzinfo=UTC)
    threshold = timedelta(days=days_threshold)

    def is_old(pr, dt):
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

    for monday in mondays:
        dt = datetime.combine(monday, time(), tzinfo=UTC)
        valid_prs = [pr for pr in prs if is_old(pr, dt)]
        valid_prs = drop_archived_prs(valid_prs, monday)

        name = f"queue_older_than_{days_threshold}_days"

        log.info(
            "%s | %s | Processing %s old PRs at %s",
            name,
            org,
            len(valid_prs),
            dt,
        )
        yield from iter_prs(valid_prs, monday, name)


def pr_throughput(prs, org):
    """
    PRs closed each day from the earliest day to today
    """
    start = min([pr["created_at"] for pr in prs]).date()
    days = list(iter_days(start, date.today()))

    for day in days:
        valid_prs = drop_archived_prs(prs, day)
        merged_prs = [
            pr for pr in valid_prs if pr["merged_at"] and pr["merged_at"].date() == day
        ]

        log.info("%s | %s | Processing %s merged PRs", day, org, len(merged_prs))
        yield from iter_prs(merged_prs, day, name="prs_merged")


@click.command()
@click.pass_context
def github(ctx):
    ctx.ensure_object(dict)

    timescaledb.reset_table(timescaledb.GitHubPullRequests)

    GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
    orgs = [
        "ebmdatalab",
        "opensafely-core",
    ]
    for org in orgs:
        log.info("Working with org: %s", org)
        client = api.GitHubClient(org, GITHUB_TOKEN)
        prs = list(api.iter_prs(client))
        log.info("Backfilling with %s PRs for %s", len(prs), org)

        rows = itertools.chain(
            old_prs(prs, org, days_threshold=7),
            pr_throughput(prs, org),
        )

        timescaledb.write(timescaledb.GitHubPullRequests, rows)
