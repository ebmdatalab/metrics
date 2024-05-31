import sys

import structlog

import metrics.github.github as github
from metrics.github.metrics import convert_codespaces_to_dicts
from metrics.timescaledb import db, tables


log = structlog.get_logger()


def main():
    log.info("Getting codespaces")
    codespaces = github.codespaces(org="opensafely")
    log.info(f"Got {len(codespaces)} codespaces")

    log.info("Writing data")
    db.upsert(tables.GitHubCodespaces, convert_codespaces_to_dicts(codespaces))
    log.info("Written data")


if __name__ == "__main__":
    sys.exit(main())
