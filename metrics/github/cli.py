from datetime import timedelta

import click
import structlog

from .. import influxdb
from . import api
from .prs import process_prs


log = structlog.get_logger()
writer = influxdb.write


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
    process_prs(writer, f"queue{suffix}", prs, date)


@github.command()
@click.argument("org")
@click.argument("date", type=click.DateTime())
@click.option("--days", default=7, type=int)
@click.pass_context
def pr_throughput(ctx, org, date, days):
    """PRs opened in the last number of days given"""
    end = date.date()
    start = date - timedelta(days=days)

    prs = api.prs_opened_in_the_last_N_days(org, start, end)

    log.info("%s | %s | Processing %s PRs", date, org, len(prs))
    process_prs(writer, "throughput", prs, date)
