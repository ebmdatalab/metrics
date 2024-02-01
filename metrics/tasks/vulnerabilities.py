import os
import sys
from datetime import date, timedelta

import structlog

from metrics import timescaledb
from metrics.github.client import GitHubClient
from metrics.github.security import vulnerabilities


log = structlog.get_logger()


def main():
    os_core_token = os.environ["GITHUB_OS_CORE_TOKEN"]
    ebmdatalab_token = os.environ["GITHUB_EBMDATALAB_TOKEN"]
    yesterday = date.today() - timedelta(days=1)

    client = GitHubClient(ebmdatalab_token)
    log.info("Fetching vulnerabilities for ebmdatalab")
    ebmdatalab_vulns = list(vulnerabilities(client, "ebmdatalab", yesterday))

    client = GitHubClient(os_core_token)
    log.info("Fetching vulnerabilities for opensafely-core")
    os_core_vulns = list(vulnerabilities(client, "opensafely-core", yesterday))

    timescaledb.reset_table(timescaledb.GitHubVulnerabilities)
    timescaledb.write(timescaledb.GitHubVulnerabilities, ebmdatalab_vulns)
    timescaledb.write(timescaledb.GitHubVulnerabilities, os_core_vulns)


if __name__ == "__main__":
    sys.exit(main())
