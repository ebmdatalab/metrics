import sys

import structlog

from metrics.github.github import tech_issues
from metrics.github.metrics import get_issues_metrics
from metrics.timescaledb import db, tables


log = structlog.get_logger()


def main():
    log.info("Getting metrics")
    issues = tech_issues()
    log.info(f"Got {len(issues)} issues")

    metrics = get_issues_metrics(issues)
    log.info("Got metrics")

    log.info("Writing data")
    db.reset_table(tables.GitHubIssues)
    db.write(tables.GitHubIssues, metrics)
    log.info("Written data")


if __name__ == "__main__":
    sys.exit(main())
