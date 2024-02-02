import os
import sys

import structlog

from metrics import timescaledb
from metrics.github.client import GitHubClient
from metrics.github.prs import get_metrics


log = structlog.get_logger()


def main():
    client = GitHubClient(
        tokens={
            "ebmdatalab": os.environ["GITHUB_EBMDATALAB_TOKEN"],
            "opensafely-core": os.environ["GITHUB_OS_CORE_TOKEN"],
        }
    )

    log.info("Working with org: ebmdatalab")
    ebmdatalab_metrics = get_metrics(client, "ebmdatalab")

    log.info("Working with org: opensafely-core")
    os_core_metrics = get_metrics(client, "opensafely-core")

    metrics = ebmdatalab_metrics + os_core_metrics

    timescaledb.reset_table(timescaledb.GitHubPullRequests)
    timescaledb.write(timescaledb.GitHubPullRequests, metrics)


if __name__ == "__main__":
    sys.exit(main())
