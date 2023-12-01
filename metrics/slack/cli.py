import itertools
from datetime import datetime

import click
import structlog
from sqlalchemy import create_engine

from ..timescaledb import TimescaleDBWriter, drop_tables
from ..timescaledb.tables import SlackTechSupport
from ..timescaledb.writer import TIMESCALEDB_URL
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
        drop_tables(connection, prefix="slack_")
    log.info("Dropped existing slack_* tables")

    with TimescaleDBWriter(SlackTechSupport) as writer:
        for date, messages in itertools.groupby(
            messages, lambda m: datetime.fromtimestamp(float(m["ts"])).date()
        ):
            writer.write(date, len(list(messages)), name="requests")
