import sys

import structlog

from metrics.github.github import tech_prs
from metrics.github.metrics import get_pr_metrics
from metrics.timescaledb import db, tables


log = structlog.get_logger()


def main():
    log.info("Getting metrics")
    orgs = ["ebmdatalab", "opensafely-core"]
    prs = tech_prs(orgs)
    log.info(
        f"Got {sum(len(ps) for ps in prs.values())} PRs from {len(prs.keys())} repos"
    )

    metrics = get_pr_metrics(prs)
    log.info("Got metrics")

    log.info("Writing data")
    db.reset_table(tables.GitHubPullRequests)
    db.write(tables.GitHubPullRequests, metrics)
    log.info("Written data")


if __name__ == "__main__":
    sys.exit(main())
