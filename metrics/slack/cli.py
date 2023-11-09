import itertools
from datetime import datetime

import click

from ..timescaledb import TimescaleDBWriter
from .api import get_app, iter_messages


@click.group()
@click.option("--signing-secret", required=True, envvar="SLACK_SIGNING_SECRET")
@click.option("--token", required=True, envvar="SLACK_TOKEN")
@click.pass_context
def slack(ctx, signing_secret, token):
    ctx.ensure_object(dict)

    ctx.obj["SLACK_SIGNING_SECRET"] = signing_secret
    ctx.obj["SLACK_TOKEN"] = token


@slack.command()
@click.argument("date", type=click.DateTime(), required=False)
@click.option(
    "--tech-support-channel-id", required=True, envvar="SLACK_TECH_SUPPORT_CHANNEL_ID"
)
@click.option("--backfill", is_flag=True)
@click.pass_context
def tech_support(ctx, date, tech_support_channel_id, backfill):
    if backfill and date:
        raise click.BadParameter("--backfill cannot be used with a date")

    day = None if backfill else date.date()

    app = get_app(ctx.obj["SLACK_SIGNING_SECRET"], ctx.obj["SLACK_TOKEN"])

    messages = iter_messages(app, tech_support_channel_id, date=day)

    with TimescaleDBWriter("slack_tech_support", "requests") as writer:
        for date, messages in itertools.groupby(
            messages, lambda m: datetime.fromtimestamp(float(m["ts"])).date()
        ):
            writer.write(date, len(list(messages)))