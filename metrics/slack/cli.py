import itertools
from datetime import datetime, time

import click
import structlog

from .. import timescaledb
from .api import get_app, iter_messages


log = structlog.get_logger()


@click.group()
@click.option("--signing-secret", required=True, envvar="SLACK_SIGNING_SECRET")
@click.option("--token", required=True, envvar="SLACK_TOKEN")
@click.pass_context
def slack(ctx, signing_secret, token):
    ctx.ensure_object(dict)

    ctx.obj["SLACK_SIGNING_SECRET"] = signing_secret
    ctx.obj["SLACK_TOKEN"] = token


@slack.command()
@click.option(
    "--tech-support-channel-id", required=True, envvar="SLACK_TECH_SUPPORT_CHANNEL_ID"
)
@click.pass_context
def tech_support(ctx, tech_support_channel_id):
    app = get_app(ctx.obj["SLACK_SIGNING_SECRET"], ctx.obj["SLACK_TOKEN"])

    messages = iter_messages(app, tech_support_channel_id)

    rows = []
    for date, messages in itertools.groupby(
        messages, lambda m: datetime.fromtimestamp(float(m["ts"])).date()
    ):
        rows.append(
            {
                "time": datetime.combine(date, time()),
                "value": len(list(messages)),
                "name": "requests",
            }
        )

    timescaledb.reset_table(timescaledb.SlackTechSupport)
    timescaledb.write(timescaledb.SlackTechSupport, rows)
