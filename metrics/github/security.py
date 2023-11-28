import os
from datetime import datetime, timedelta

import requests
import structlog


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
        print(response.headers)
        print(response.content)

    response.raise_for_status()
    return response.json()


def get_vulnerabilities(org):
    query = """
    query vulnerabilities($org: String!) {
      organization(login: $org) {
        repositories(first: 100) {
          nodes {
            name
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
        if not alerts:
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


def print_vulnerabilities(vulns):  # pragma: no cover
    print(f"There are {len(vulns)} alerts")
    print(parse_vulnerabilities(vulns))


if __name__ == "__main__":  # pragma: no cover
    print_vulnerabilities(get_vulnerabilities())
