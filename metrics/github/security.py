import os
from dataclasses import dataclass
from datetime import date, timedelta

import structlog

from .. import timescaledb
from ..tools import dates
from . import api


log = structlog.get_logger()


def query_repos(client):
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


def query_vulnerabilities(client, repo):
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

    return client.get_query(
        query,
        path=["organization", "repository", "vulnerabilityAlerts"],
        org=client.org,
        repo=repo["name"],
    )


@dataclass
class Vulnerability:
    created_at: date
    fixed_at: date
    dismissed_at: date

    def is_open_at(self, target_date):
        return self.created_at <= target_date and not self.is_closed_at(target_date)

    def is_closed_at(self, target_date):
        return (self.fixed_at is not None and self.fixed_at <= target_date) or (
            self.dismissed_at is not None and self.dismissed_at <= target_date
        )

    @staticmethod
    def from_dict(my_dict):
        return Vulnerability(
            dates.date_from_iso(my_dict["createdAt"]),
            dates.date_from_iso(my_dict["fixedAt"]),
            dates.date_from_iso(my_dict["dismissedAt"]),
        )


@dataclass
class Repo:
    name: str
    org: str
    vulnerabilities: list[Vulnerability]

    def __post_init__(self):
        self.vulnerabilities = sorted(self.vulnerabilities, key=lambda v: v.created_at)

    def earliest_date(self):
        return self.vulnerabilities[0].created_at


def get_repos(client):
    for repo in query_repos(client):
        if repo["archivedAt"]:
            continue

        vulnerabilities = []
        for vuln in query_vulnerabilities(client, repo):
            vulnerabilities.append(Vulnerability.from_dict(vuln))

        if vulnerabilities:
            yield Repo(repo["name"], client.org, vulnerabilities)


def vulnerabilities(client, to_date):
    for repo in get_repos(client):
        for day in dates.iter_days(repo.earliest_date(), to_date):
            closed_vulns = sum([1 for v in repo.vulnerabilities if v.is_closed_at(day)])
            open_vulns = sum([1 for v in repo.vulnerabilities if v.is_open_at(day)])

            yield {
                "time": day,
                "closed": closed_vulns,
                "open": open_vulns,
                "organisation": repo.org,
                "repo": repo.name,
                "value": 0,  # needed for the timescaledb
            }


if __name__ == "__main__":  # pragma: no cover
    timescaledb.reset_table(timescaledb.GitHubVulnerabilities)

    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
    os_core_token = os.environ.get("GITHUB_OS_CORE_TOKEN", GITHUB_TOKEN)
    ebmdatalab_token = os.environ.get("GITHUB_EBMDATALAB_TOKEN", GITHUB_TOKEN)
    yesterday = date.today() - timedelta(days=1)

    client = api.GitHubClient("ebmdatalab", ebmdatalab_token)
    log.info("Fetching vulnerabilities for %s", client.org)
    timescaledb.write(
        timescaledb.GitHubVulnerabilities, vulnerabilities(client, yesterday)
    )

    client = api.GitHubClient("opensafely-core", os_core_token)
    log.info("Fetching vulnerabilities for %s", client.org)
    timescaledb.write(
        timescaledb.GitHubVulnerabilities, vulnerabilities(client, yesterday)
    )
