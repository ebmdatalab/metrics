import os
import sys
from datetime import date, timedelta

import structlog

from metrics.github.client import GitHubClient
from metrics.github.security import vulnerabilities
from metrics.timescaledb import db, tables


log = structlog.get_logger()


def main():
    os_core_token = os.environ["GITHUB_OS_CORE_TOKEN"]
    ebmdatalab_token = os.environ["GITHUB_EBMDATALAB_TOKEN"]
    yesterday = date.today() - timedelta(days=1)

    client = GitHubClient(ebmdatalab_token)
    log.info("Fetching vulnerabilities for ebmdatalab")
    ebmdatalab_vulns = vulnerabilities(client, "ebmdatalab", yesterday)

    client = GitHubClient(os_core_token)
    log.info("Fetching vulnerabilities for opensafely-core")
    os_core_vulns = vulnerabilities(client, "opensafely-core", yesterday)

    db.reset_table(tables.GitHubVulnerabilities)
    db.write(tables.GitHubVulnerabilities, ebmdatalab_vulns)
    db.write(tables.GitHubVulnerabilities, os_core_vulns)


if __name__ == "__main__":
    sys.exit(main())
