import click

from .github.cli import github
from .logs import setup_logging
from .slack.cli import slack


@click.group()
@click.option("--debug", default=False, is_flag=True)
@click.option("--timescaledb-url", required=True, envvar="TIMESCALEDB_URL")
@click.pass_context
def cli(ctx, debug, timescaledb_url):
    ctx.ensure_object(dict)

    setup_logging(debug)

    ctx.obj["DEBUG"] = debug
    ctx.obj["TIMESCALEDB_URL"] = timescaledb_url


cli.add_command(github)
cli.add_command(slack)
