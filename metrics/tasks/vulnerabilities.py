import sys
from datetime import date, timedelta

import structlog

from metrics.github.security import vulnerabilities
from metrics.timescaledb import db, tables


log = structlog.get_logger()


def main():
    yesterday = date.today() - timedelta(days=1)

    log.info("Fetching vulnerabilities")
    vulns = vulnerabilities(yesterday)

    db.reset_table(tables.GitHubVulnerabilities)
    db.write(tables.GitHubVulnerabilities, vulns)


if __name__ == "__main__":
    sys.exit(main())
