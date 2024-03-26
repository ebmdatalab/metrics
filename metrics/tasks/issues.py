import sys

import structlog

from metrics.github import issues
from metrics.timescaledb import db, tables


log = structlog.get_logger()


def main():
    log.info("Getting metrics")
    metrics = issues.get_metrics(["ebmdatalab", "opensafely-core"])
    log.info("Got metrics")

    log.info("Writing data")
    db.reset_table(tables.GitHubIssues)
    db.write(tables.GitHubIssues, metrics)
    log.info("Written data")


if __name__ == "__main__":
    sys.exit(main())
