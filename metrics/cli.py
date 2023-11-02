import click

from .github.cli import github
from .logs import setup_logging


@click.group()
@click.option("--debug", default=False, is_flag=True)
@click.pass_context
def cli(ctx, debug):
    ctx.ensure_object(dict)

    setup_logging(debug)

    ctx.obj["DEBUG"] = debug


cli.add_command(github)
