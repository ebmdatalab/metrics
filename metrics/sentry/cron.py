import os

import sentry_sdk
from sentry_sdk.crons import capture_checkin
from sentry_sdk.crons.consts import MonitorStatus


class Cron:
    def __init__(self):
        sentry_sdk.init(
            dsn=os.environ.get("SENTRY_DSN"),
        )

    _monitor_config = {
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

    def get_monitor(self, modname):
        monitor_slug = f"metrics-{modname}"
        return self.Monitor(monitor_slug, self._monitor_config)

    class Monitor:
        def __init__(self, monitor_slug, monitor_config):
            self.monitor_slug = monitor_slug
            self.monitor_config = monitor_config
            self.check_in_id = None

        def _checkin(self, status):
            check_in_id = capture_checkin(
                monitor_slug=self.monitor_slug,
                monitor_config=self.monitor_config,
                status=status,
                check_in_id=self.check_in_id,
            )
            if not self.check_in_id:
                self.check_in_id = check_in_id

        def in_progress(self):
            self._checkin(status=MonitorStatus.IN_PROGRESS)

        def ok(self):
            self._checkin(status=MonitorStatus.OK)

        def error(self):
            self._checkin(status=MonitorStatus.ERROR)
