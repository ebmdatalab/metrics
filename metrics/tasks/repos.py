import sys

import structlog

from metrics.github.github import all_repos
from metrics.timescaledb import db, tables


log = structlog.get_logger()


def main():
    log.info("Getting repos")
    orgs = ["ebmdatalab", "opensafely-core"]
    repos = [repo for org in orgs for repo in all_repos(org)]
    log.info("Got repos")

    data = [dict(organisation=r.org, repo=r.name, owner=r.team) for r in repos]

    log.info("Writing data")
    db.reset_table(tables.GitHubRepos)
    db.write(tables.GitHubRepos, data)
    log.info("Written data")


if __name__ == "__main__":
    sys.exit(main())
