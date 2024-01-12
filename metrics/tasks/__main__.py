import pkgutil

import structlog

import metrics.tasks


log = structlog.get_logger()

for _, modname, _ in pkgutil.iter_modules(metrics.tasks.__path__):
    if modname != "__main__":
        log.info(f"Found {modname}")
        try:
            pkgutil.resolve_name(f"metrics.tasks.{modname}").main()
        except AttributeError as error:
            log.error(f"Skipping {modname} because {error}")
        except Exception as exc:
            log.error(f"Failed to run {modname} because because an error occurred.")
            log.exception(exc)
