import sys
from datetime import date, timedelta

import structlog

from metrics.github.security import vulnerabilities
from metrics.timescaledb import db, tables


log = structlog.get_logger()


def main():
    yesterday = date.today() - timedelta(days=1)

    log.info("Fetching vulnerabilities for ebmdatalab")
    ebmdatalab_vulns = vulnerabilities("ebmdatalab", yesterday)

    log.info("Fetching vulnerabilities for opensafely-core")
    os_core_vulns = vulnerabilities("opensafely-core", yesterday)

    db.reset_table(tables.GitHubVulnerabilities)
    db.write(tables.GitHubVulnerabilities, ebmdatalab_vulns)
    db.write(tables.GitHubVulnerabilities, os_core_vulns)


if __name__ == "__main__":
    sys.exit(main())
