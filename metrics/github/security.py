import os
from datetime import datetime, timedelta

import requests
import structlog
from sqlalchemy import create_engine

from ..timescaledb import TimescaleDBWriter, drop_tables
from ..timescaledb.tables import GitHubVulnerabilities
from ..timescaledb.writer import TIMESCALEDB_URL


log = structlog.get_logger()

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]

session = requests.Session()
session.headers = {
    "Authorization": f"bearer {GITHUB_TOKEN}",
    "User-Agent": "Bennett Metrics Testing",
}


def make_request(query, variables):
    response = session.post(
        "https://api.github.com/graphql", json={"query": query, "variables": variables}
    )

    if not response.ok:
        log.info(response.headers)
        log.info(response.content)

    response.raise_for_status()
    return response.json()


def get_vulnerabilities(org):
    query = """
    query vulnerabilities($org: String!) {
      organization(login: $org) {
        repositories(first: 100) {
          nodes {
            name
            archivedAt
            vulnerabilityAlerts(first: 100) {
              nodes {
                number
                createdAt
                fixedAt
                dismissedAt
              }
              pageInfo {
                hasNextPage endCursor
              }
            }
          }
        }
      }
    }
    """
    variables = {"org": org}
    response = make_request(query, variables)
    return response["data"]["organization"]["repositories"]["nodes"]


def date_before(date_string, target_date):
    if not date_string:
        return False

    return datetime.fromisoformat(date_string).date() <= target_date


def parse_vulnerabilities_for_date(vulns, repo, target_date, org):
    closed_vulns = 0
    open_vulns = 0
    for row in vulns:
        if date_before(row["fixedAt"], target_date) or date_before(
            row["dismissedAt"], target_date
        ):
            closed_vulns += 1
        elif date_before(row["createdAt"], target_date):
            open_vulns += 1

    return {
        "date": target_date,
        "closed": closed_vulns,
        "open": open_vulns,
        "organisation": org,
        "repo": repo,
    }


def parse_vulnerabilities(vulnerabilities, org):
    results = []

    for repo in vulnerabilities:
        repo_name = repo["name"]
        alerts = repo["vulnerabilityAlerts"]["nodes"]

        if repo["archivedAt"] or not alerts:
            continue

        earliest_date = datetime.fromisoformat(alerts[0]["createdAt"]).date()
        latest_date = datetime.fromisoformat(alerts[-1]["createdAt"]).date()
        one_day = timedelta(days=1)

        while earliest_date <= latest_date:
            results.append(
                parse_vulnerabilities_for_date(alerts, repo_name, earliest_date, org)
            )
            earliest_date += one_day

    return results


def vulnerabilities(org):
    vulns = parse_vulnerabilities(get_vulnerabilities(org), org)
    with TimescaleDBWriter(GitHubVulnerabilities) as writer:
        for v in vulns:
            date = v.pop("date")
            writer.write(date, value=0, **v)


if __name__ == "__main__":  # pragma: no cover
    log.info("Dropping existing github_vulnerabilities table")
    engine = create_engine(TIMESCALEDB_URL)
    with engine.begin() as connection:
        drop_tables(connection, prefix="github_vulnerabilities")
    log.info("Dropped existing github_vulnerabilities table")

    vulnerabilities("ebmdatalab")
    vulnerabilities("opensafely-core")
