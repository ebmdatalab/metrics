import os
import sys

import structlog

from metrics import timescaledb
from metrics.github.client import GitHubClient
from metrics.github.prs import fetch_prs, old_prs, pr_throughput


log = structlog.get_logger()


def main():
    ebmdatalab_token = os.environ["GITHUB_EBMDATALAB_TOKEN"]
    os_core_token = os.environ["GITHUB_OS_CORE_TOKEN"]

    ebmdatalab_metrics = get_metrics("ebmdatalab", ebmdatalab_token)
    os_core_metrics = get_metrics("opensafely-core", os_core_token)
    metrics = ebmdatalab_metrics + os_core_metrics

    timescaledb.reset_table(timescaledb.GitHubPullRequests)
    timescaledb.write(timescaledb.GitHubPullRequests, metrics)


def get_metrics(org, ebmdatalab_token):
    client = GitHubClient(ebmdatalab_token)
    log.info(f"Working with org: {org}")
    prs = fetch_prs(client, org)
    return old_prs(prs, days_threshold=7) + pr_throughput(prs)


if __name__ == "__main__":
    sys.exit(main())
