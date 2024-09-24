import sys

import pandas as pd
import structlog

from metrics.github.github import tech_prs


log = structlog.get_logger()


def main():
    log.info("Getting metrics")
    prs = tech_prs()
    log.info(f"Got {len(prs)} PRs")

    df = pd.DataFrame.from_records(prs)

    # metrics = get_pr_metrics(prs)
    # log.info("Got metrics")
    #
    # log.info("Writing data")
    # db.reset_table(tables.GitHubPullRequests)
    # db.write(tables.GitHubPullRequests, metrics)
    # log.info("Written data")


if __name__ == "__main__":
    sys.exit(main())
