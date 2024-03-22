import itertools
import os
import sys
from datetime import datetime, time

import structlog

from metrics.slack.api import get_app, iter_messages
from metrics.timescaledb import db, tables


log = structlog.get_logger()


def main():
    slack_signing_secret = os.environ["SLACK_SIGNING_SECRET"]
    slack_token = os.environ["SLACK_TOKEN"]
    tech_support_channel_id = os.environ["SLACK_TECH_SUPPORT_CHANNEL_ID"]

    app = get_app(slack_signing_secret, slack_token)
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

    db.reset_table(tables.SlackTechSupport)
    db.write(tables.SlackTechSupport, rows)


if __name__ == "__main__":
    sys.exit(main())
