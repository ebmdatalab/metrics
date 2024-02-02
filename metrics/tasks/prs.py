import os
import sys

from metrics import timescaledb
from metrics.github.client import GitHubClient
from metrics.github.prs import get_metrics


def main():
    client = GitHubClient(
        tokens={
            "ebmdatalab": os.environ["GITHUB_EBMDATALAB_TOKEN"],
            "opensafely-core": os.environ["GITHUB_OS_CORE_TOKEN"],
        }
    )

    metrics = get_metrics(client, ["ebmdatalab", "opensafely-core"])

    timescaledb.reset_table(timescaledb.GitHubPullRequests)
    timescaledb.write(timescaledb.GitHubPullRequests, metrics)


if __name__ == "__main__":
    sys.exit(main())
