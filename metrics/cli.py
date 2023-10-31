import click

from .github import commands as github_commands
from .logs import setup_logging


@click.group()
@click.option("--debug", default=False, is_flag=True)
@click.pass_context
def cli(ctx, debug):
    ctx.ensure_object(dict)

    setup_logging(debug)

    ctx.obj["DEBUG"] = debug


@cli.group()
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
    date = date.date()

    github_commands.pr_queue(org, date, days_threshold)


@github.command()
@click.argument("org")
@click.argument("date", type=click.DateTime())
@click.option("--days", default=7, type=int)
@click.pass_context
def pr_throughput(ctx, org, date, days):
    date = date.date()

    github_commands.pr_throughput(org, date, days)
