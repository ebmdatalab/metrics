import json
import os

import requests
import structlog

from .. import timescaledb
from ..tools import dates


log = structlog.get_logger()

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]

session = requests.Session()


class GitHubClient:
    def __init__(self, org, token):
        self.org = org
        self.token = token

    def post(self, query):
        session.headers = {
            "Authorization": f"bearer {self.token}",
            "User-Agent": "Bennett Metrics",
        }
        response = session.post(
            "https://api.github.com/graphql",
            json={"query": query, "variables": {"org": self.org}},
        )

        if not response.ok:
            log.info(response.headers)
            log.info(response.content)

        response.raise_for_status()
        return response.json()


def get_vulnerabilities(client):
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

    response = client.make_request(query)
    if "data" not in response:
        raise RuntimeError(json.dumps(response, indent=2))

    return response["data"]["organization"]["repositories"]["nodes"]


def date_before(date_string, target_date):
    if not date_string:
        return False

    return dates.date_from_iso(date_string) <= target_date


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

        earliest_date = dates.date_from_iso(alerts[0]["createdAt"])
        latest_date = dates.date_from_iso(alerts[-1]["createdAt"])

        for day in dates.iter_days(earliest_date, latest_date):
            results.append(parse_vulnerabilities_for_date(alerts, repo_name, day, org))

    return results


def vulnerabilities(client):
    vulns = parse_vulnerabilities(get_vulnerabilities(client), client.org)

    rows = []
    for v in vulns:
        date = v.pop("date")
        rows.append({"time": date, "value": 0, **v})

    timescaledb.write(timescaledb.GitHubVulnerabilities, rows)


if __name__ == "__main__":  # pragma: no cover
    timescaledb.reset_table(timescaledb.GitHubVulnerabilities)

    client = GitHubClient("ebmdatalab", GITHUB_TOKEN)
    vulnerabilities(client)

    client = GitHubClient("opensafely-core", GITHUB_TOKEN)
    vulnerabilities(client)
