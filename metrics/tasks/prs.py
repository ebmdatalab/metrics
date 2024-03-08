import os
import sys

import structlog

from metrics.github.client import GitHubClient
from metrics.github.prs import get_metrics
from metrics.timescaledb import db, tables


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
    db.reset_table(tables.GitHubPullRequests)
    db.write(tables.GitHubPullRequests, metrics)
    log.info("Written data")


if __name__ == "__main__":
    sys.exit(main())
