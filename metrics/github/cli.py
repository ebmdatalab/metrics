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
@click.option("--days-threshold", type=int)
@click.pass_context
def pr_queue(ctx, org, date, days_threshold):
    """The number of PRs open on the given date"""
    date = date.date()
    prs = api.prs_open_on_date(org, date)

    if days_threshold is not None:
        # remove PRs which have been open <days_threshold days
        prs = [
            pr
            for pr in prs
            if (pr["closed"] - pr["created"]) >= timedelta(days=days_threshold)
        ]

    suffix = f"_older_than_{days_threshold}_days" if days_threshold else ""

    log.info("%s | %s | Processing %s PRs", date, org, len(prs))
    with TimescaleDBWriter("github_pull_requests", f"queue{suffix}") as writer:
        process_prs(writer, prs, date)


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
