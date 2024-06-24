import os

import sentry_sdk


def init():
    sentry_sdk.init(
        dsn=os.environ.get("SENTRY_DSN"),
    )


monitor_config = {
    "schedule": {"type": "crontab", "value": "@daily"},
    "timezone": "Etc/UTC",
    # If an expected check-in doesn't come in `checkin_margin`
    # minutes, it'll be considered missed
    "checkin_margin": 30,
    # The check-in is allowed to run for `max_runtime` minutes
    # before it's considered failed
    "max_runtime": 10,
    # It'll take `failure_issue_threshold` consecutive failed
    # check-ins to create an issue
    "failure_issue_threshold": 1,
    # It'll take `recovery_threshold` OK check-ins to resolve
    # an issue
    "recovery_threshold": 1,
}
