import sys

import structlog


log = structlog.get_logger()


def main():
    log.info("Smoke test task ran successfully")


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
