import os
import sys

import structlog

from metrics.github.client import GitHubClient
from metrics.github.repos import get_repo_ownership
from metrics.timescaledb import db, tables


log = structlog.get_logger()


def main():
    client = GitHubClient(
        tokens={
            "ebmdatalab": os.environ["GITHUB_EBMDATALAB_TOKEN"],
            "opensafely-core": os.environ["GITHUB_OS_CORE_TOKEN"],
        }
    )

    log.info("Getting repos")
    repos = get_repo_ownership(client, ["ebmdatalab", "opensafely-core"])
    log.info("Got repos")

    log.info("Writing data")
    db.reset_table(tables.GitHubRepos)
    db.write(tables.GitHubRepos, repos)
    log.info("Written data")


if __name__ == "__main__":
    sys.exit(main())
