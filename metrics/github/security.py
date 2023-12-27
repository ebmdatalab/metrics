import os

import structlog

from .. import timescaledb
from ..tools import dates
from . import api


log = structlog.get_logger()


def fetch_repos(client):
    query = """
    query repos($cursor: String, $org: String!) {
      organization(login: $org) {
        repositories(first: 100, after: $cursor) {
          nodes {
            name
            archivedAt
          }
          pageInfo {
              endCursor
              hasNextPage
          }
        }
      }
    }
    """
    return client.get_query(query, path=["organization", "repositories"])


def fetch_vulnerabilities(client):
    query = """
    query vulnerabilities($cursor: String, $org: String!, $repo: String!) {
      organization(login: $org) {
        repository(name: $repo) {
          name
          vulnerabilityAlerts(first: 100, after: $cursor) {
            nodes {
              createdAt
              fixedAt
              dismissedAt
            }
            pageInfo {
              endCursor
              hasNextPage
            }
          }
        }
      }
    }
    """

    repos = []
    for repo in fetch_repos(client):
        if repo["archivedAt"]:
            continue

        vulnerabilities = list(
            client.get_query(
                query,
                path=["organization", "repository", "vulnerabilityAlerts"],
                org=client.org,
                repo=repo["name"],
            )
        )

        if vulnerabilities:
            repos.append({"repo": repo["name"], "vulnerabilities": vulnerabilities})

    return repos


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


def parse_vulnerabilities(repos, org):
    for repo in repos:
        repo_name = repo["repo"]
        vulnerabilities = repo["vulnerabilities"]

        earliest_date = dates.date_from_iso(vulnerabilities[0]["createdAt"])
        latest_date = dates.date_from_iso(vulnerabilities[-1]["createdAt"])

        for day in dates.iter_days(earliest_date, latest_date):
            yield parse_vulnerabilities_for_date(vulnerabilities, repo_name, day, org)


def vulnerabilities(client):
    vulns = parse_vulnerabilities(fetch_vulnerabilities(client), client.org)

    rows = []
    for v in vulns:
        date = v.pop("date")
        rows.append({"time": date, "value": 0, **v})

    timescaledb.write(timescaledb.GitHubVulnerabilities, rows)


if __name__ == "__main__":  # pragma: no cover
    timescaledb.reset_table(timescaledb.GitHubVulnerabilities)

    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
    os_core_token = os.environ.get("GITHUB_OS_CORE_TOKEN", GITHUB_TOKEN)
    ebmdatalab_token = os.environ.get("GITHUB_EBMDATALAB_TOKEN", GITHUB_TOKEN)

    client = api.GitHubClient("ebmdatalab", ebmdatalab_token)
    log.info("Fetching vulnerabilities for %s", client.org)
    vulnerabilities(client)

    client = api.GitHubClient("opensafely-core", os_core_token)
    log.info("Fetching vulnerabilities for %s", client.org)
    vulnerabilities(client)
