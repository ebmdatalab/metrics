import json
import os

import structlog

from .. import timescaledb
from ..tools import dates
from . import api


log = structlog.get_logger()


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

    response = client.post(query, {})
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

    GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
    os_core_token = os.environ.get("GITHUB_OS_CORE_TOKEN", GITHUB_TOKEN)
    ebmdatalab_token = os.environ.get("GITHUB_EBMDATALAB_TOKEN", GITHUB_TOKEN)

    client = api.GitHubClient("ebmdatalab", ebmdatalab_token)
    vulnerabilities(client)

    client = api.GitHubClient("opensafely-core", os_core_token)
    vulnerabilities(client)
