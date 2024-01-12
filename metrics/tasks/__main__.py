import pkgutil

import structlog

import metrics.tasks


log = structlog.get_logger()

for _, modname, _ in pkgutil.iter_modules(metrics.tasks.__path__):
    log.info(f"Found {modname}")
    if modname != "__main__":
        pkgutil.resolve_name(f"metrics.tasks.{modname}").main()
