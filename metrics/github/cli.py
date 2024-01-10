import os
from datetime import UTC, date, datetime, time, timedelta

import click
import structlog

from .. import timescaledb
from ..tools.dates import iter_days, previous_weekday
from . import api
from .prs import drop_archived_prs, iter_prs


log = structlog.get_logger()


def old_prs(prs, days_threshold):
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

        yield from iter_prs(valid_prs, monday, name)


def pr_throughput(prs):
    """
    PRs closed each day from the earliest day to today
    """
    start = min([pr["created_at"] for pr in prs]).date()

    for day in iter_days(start, date.today()):
        valid_prs = drop_archived_prs(prs, day)
        merged_prs = [
            pr for pr in valid_prs if pr["merged_at"] and pr["merged_at"].date() == day
        ]

        yield from iter_prs(merged_prs, day, name="prs_merged")


@click.command()
@click.pass_context
def github(ctx):
    ctx.ensure_object(dict)

    ebmdatalab_token = os.environ["GITHUB_EBMDATALAB_TOKEN"]
    os_core_token = os.environ["GITHUB_OS_CORE_TOKEN"]

    log.info("Working with org: %s", "ebmdatalab")
    client = api.GitHubClient("ebmdatalab", ebmdatalab_token)
    prs = list(api.iter_prs(client))
    ebmdatalab_prs = old_prs(prs, days_threshold=7)
    ebmdatalab_throughput = pr_throughput(prs)

    log.info("Working with org: %s", "opensafely-core")
    client = api.GitHubClient("opensafely-core", os_core_token)
    prs = list(api.iter_prs(client))
    os_core_prs = old_prs(prs, days_threshold=7)
    os_core_throughput = pr_throughput(prs)

    timescaledb.reset_table(timescaledb.GitHubPullRequests)

    timescaledb.write(timescaledb.GitHubPullRequests, ebmdatalab_prs)
    timescaledb.write(timescaledb.GitHubPullRequests, ebmdatalab_throughput)

    timescaledb.write(timescaledb.GitHubPullRequests, os_core_prs)
    timescaledb.write(timescaledb.GitHubPullRequests, os_core_throughput)
