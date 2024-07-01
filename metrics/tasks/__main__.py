import pkgutil

import structlog

import metrics.tasks
from metrics.sentry.cron import Cron


log = structlog.get_logger()
sentry_cron = Cron()

for _, modname, _ in pkgutil.iter_modules(metrics.tasks.__path__):
    if modname != "__main__":
        log.info(f"Found {modname}")
        monitor = sentry_cron.get_monitor(modname)
        monitor.in_progress()
        try:
            pkgutil.resolve_name(f"metrics.tasks.{modname}").main()
            monitor.ok()
        except AttributeError as error:
            log.error(f"Skipping {modname} because {error}")
            monitor.error()
        except Exception as exc:
            log.error(f"Failed to run {modname} because because an error occurred.")
            log.exception(exc)
            monitor.error()
