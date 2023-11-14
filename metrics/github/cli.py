from datetime import timedelta

import click
import structlog

from ..timescaledb import TimescaleDBWriter
from ..timescaledb.tables import GitHubPullRequests
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
@click.argument("days-threshold", type=int)
@click.pass_context
def open_prs(ctx, org, date, days_threshold):
    """The number of PRs open for DAYS_THRESHOLD or longer on the given date"""
    date = date.date()
    prs = api.prs_open_on_date(org, date)

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
