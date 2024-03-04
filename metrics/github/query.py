import itertools
import os
from dataclasses import dataclass
from datetime import date

from metrics.github.repos import NON_TECH_REPOS
from metrics.tools.dates import date_from_iso


def repos(client, org):
    query = """
    query repos($cursor: String, $org: String!) {
      organization(login: $org) {
        repositories(first: 100, after: $cursor) {
          nodes {
            name
            createdAt
            archivedAt
            hasVulnerabilityAlertsEnabled
          }
          pageInfo {
              endCursor
              hasNextPage
          }
        }
      }
    }
    """
    for raw_repo in maybe_truncate(
        client.get_query(query, path=["organization", "repositories"], org=org)
    ):
        repo = Repo(
            org,
            raw_repo["name"],
            date_from_iso(raw_repo["createdAt"]),
            date_from_iso(raw_repo["archivedAt"]),
            raw_repo["hasVulnerabilityAlertsEnabled"],
        )
        if repo.is_tech_owned():
            yield repo


@dataclass(frozen=True)
class Repo:
    org: str
    name: str
    created_on: date
    archived_on: date | None
    has_vulnerability_alerts_enabled: bool

    def is_tech_owned(self):
        # We use a deny-list rather than an allow-list so that newly created repos are treated as
        # Tech-owned by default, in the hopes of minimizing surprise.
        return not (
            self.org in NON_TECH_REPOS and self.name in NON_TECH_REPOS[self.org]
        )


def vulnerabilities(client, repo):
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
        org=repo.org,
        repo=repo.name,
    )


def prs(client, repo):
    query = """
    query prs($cursor: String, $org: String!, $repo: String!) {
      organization(login: $org) {
        repository(name: $repo) {
          pullRequests(first: 100, after: $cursor) {
            nodes {
              author {
                login
              }
              number
              createdAt
              closedAt
              mergedAt
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
    for pr in maybe_truncate(
        client.get_query(
            query,
            path=["organization", "repository", "pullRequests"],
            org=repo.org,
            repo=repo.name,
        )
    ):
        yield {
            "org": repo.org,
            "repo": repo.name,
            "author": pr["author"]["login"],
            "closed_on": date_from_iso(pr["closedAt"]),
            "created_on": date_from_iso(pr["createdAt"]),
            "merged_on": date_from_iso(pr["mergedAt"]),
        }


def maybe_truncate(it):
    if "DEBUG_FAST" in os.environ:
        return itertools.islice(it, 5)
    return it
