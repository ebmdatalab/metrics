from datetime import timedelta

import click
import structlog

from ..timescaledb import TimescaleDBWriter
from ..timescaledb.tables import GitHubPullRequests
from ..tools.dates import previous_weekday
from . import api
from .backfill import backfill
from .prs import process_prs


log = structlog.get_logger()


@click.group()
@click.option("--token", required=True, envvar="GITHUB_TOKEN")
@click.pass_context
def github(ctx, token):
    ctx.ensure_object(dict)

    ctx.obj["TOKEN"] = token


@github.command()
@click.argument("org")
@click.argument("date", type=click.DateTime())
@click.argument("--days-threshold", type=int, default=7)
@click.pass_context
def open_prs(ctx, org, date, days_threshold):
    """
    How many open PRs were there this week?

    The number of PRs open for DAYS_THRESHOLD (defaults to 7 days) in the
    previous week to the given date.

    Week here is defined as the dates covering the most recent Monday to Sunday
    (inclusive) before the given date, eg if the given date is a Tuesday this
    command will step back a week+1 day to collect a full weeks worth of data.
    """
    date = date.date()

    end = previous_weekday(date, 6)  # Most recent Sunday
    start = end - timedelta(days=6)  # Monday before that Sunday
    prs = api.prs_open_in_range(org, start, end)

    # remove PRs which have been open <days_threshold days
    open_prs = [
        pr
        for pr in prs
        if (pr["closed"] - pr["created"]) >= timedelta(days=days_threshold)
    ]

    log.info("%s | %s | Processing %s PRs", date, org, len(open_prs))
    with TimescaleDBWriter(GitHubPullRequests) as writer:
        process_prs(
            writer, open_prs, date, name=f"queue_older_than_{days_threshold}_days"
        )


@github.command()
@click.argument("org")
@click.argument("date", type=click.DateTime())
@click.pass_context
def pr_throughput(ctx, org, date):
    """PRs opened and PRs closed in the given day"""
    date = date.date()

    with TimescaleDBWriter(GitHubPullRequests) as writer:
        opened_prs = api.prs_opened_on_date(org, date)
        log.info("%s | %s | Processing %s opened PRs", date, org, len(opened_prs))
        process_prs(writer, opened_prs, date, name="prs_opened")

        closed_prs = api.prs_closed_on_date(org, date)
        log.info("%s | %s | Processing %s closed PRs", date, org, len(closed_prs))
        process_prs(writer, closed_prs, date, name="prs_closed")


github.add_command(backfill)
