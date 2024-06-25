import pkgutil

import structlog
from sentry_sdk.crons import capture_checkin
from sentry_sdk.crons.consts import MonitorStatus

import metrics.tasks
from metrics.sentry import sentry


log = structlog.get_logger()
sentry.init()

for _, modname, _ in pkgutil.iter_modules(metrics.tasks.__path__):
    if modname != "__main__":
        log.info(f"Found {modname}")
        monitor_slug = f"metrics-{modname}"
        status = MonitorStatus.IN_PROGRESS
        check_in_id = capture_checkin(
            monitor_slug=monitor_slug,
            status=status,
            monitor_config=sentry.monitor_config,
        )
        try:
            pkgutil.resolve_name(f"metrics.tasks.{modname}").main()
            status = MonitorStatus.OK
        except AttributeError as error:
            log.error(f"Skipping {modname} because {error}")
            status = MonitorStatus.ERROR
        except Exception as exc:
            log.error(f"Failed to run {modname} because because an error occurred.")
            log.exception(exc)
            status = MonitorStatus.ERROR
        finally:
            capture_checkin(
                monitor_slug=monitor_slug,
                status=status,
                monitor_config=sentry.monitor_config,
            )
