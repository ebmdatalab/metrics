import datetime
import sys

import structlog

from metrics.github.security import vulnerabilities
from metrics.timescaledb import db, tables


log = structlog.get_logger()


def main():
    yesterday = datetime.date.today() - datetime.timedelta(days=1)

    log.info("Fetching vulnerabilities")
    vulns = vulnerabilities(yesterday)

    db.reset_table(tables.GitHubVulnerabilities)
    db.write(tables.GitHubVulnerabilities, vulns)


if __name__ == "__main__":
    sys.exit(main())
