import itertools
import os

from metrics.github.client import GitHubClient
from metrics.tools.dates import date_from_iso


def repos(org):
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
    return maybe_truncate(
        _client().graphql_query(query, path=["organization", "repositories"], org=org)
    )


def team_repos(org, team):
    """The API doesn't make it easy for us to get all the information we need about repos in
    one place, so we just return a list of repos here and join that to the richer repo objects
    in the caller."""
    results = _client().rest_query("/orgs/{org}/teams/{team}/repos", org=org, team=team)
    for repo in results:
        yield repo["name"]


def vulnerabilities(repo):
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

    return _client().graphql_query(
        query,
        path=["organization", "repository", "vulnerabilityAlerts"],
        org=repo.org,
        repo=repo.name,
    )


def prs(repo):
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
        _client().graphql_query(
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


def issues(repo):
    query = """
    query issues($cursor: String, $org: String!, $repo: String!) {
      organization(login: $org) {
        repository(name: $repo) {
          issues(first: 100, after: $cursor) {
            nodes {
              author {
                login
              }
              createdAt
              closedAt
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
    return maybe_truncate(
        _client().graphql_query(
            query,
            path=["organization", "repository", "issues"],
            org=repo.org,
            repo=repo.name,
        )
    )


def _client():
    return GitHubClient(
        tokens={
            "ebmdatalab": os.environ["GITHUB_EBMDATALAB_TOKEN"],
            "opensafely-core": os.environ["GITHUB_OS_CORE_TOKEN"],
        }
    )


def maybe_truncate(it):
    if "DEBUG_FAST" in os.environ:
        return itertools.islice(it, 5)
    return it
