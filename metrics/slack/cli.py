import itertools
from datetime import datetime, time

import click
import structlog
from sqlalchemy import create_engine

from .. import timescaledb
from ..timescaledb.db import TIMESCALEDB_URL
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

    log.info("Dropping existing slack_* tables")
    # TODO: we have this in three places now, can we pull into some kind of
    # service wrapper?
    engine = create_engine(TIMESCALEDB_URL)
    with engine.begin() as connection:
        timescaledb.drop_tables(connection, prefix="slack_")
    log.info("Dropped existing slack_* tables")

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

    timescaledb.write(timescaledb.SlackTechSupport, rows)
