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

    log.info("Getting metrics")
    metrics = get_metrics(client, ["ebmdatalab", "opensafely-core"])
    log.info("Got metrics")

    log.info("Writing data")
    timescaledb.reset_table(timescaledb.GitHubPullRequests)
    timescaledb.write(timescaledb.GitHubPullRequests, metrics)
    log.info("Written data")


if __name__ == "__main__":
    sys.exit(main())
