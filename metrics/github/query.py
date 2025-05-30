import itertools
import os

from metrics.github.client import GitHubClient


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
    repos = _client().rest_query("/orgs/{org}/teams/{team}/repos", org=org, team=team)
    for repo in repos:
        yield repo["name"]


def team_members(org, team):
    members = _client().rest_query(
        "/orgs/{org}/teams/{team}/members", org=org, team=team
    )
    for member in members:
        yield member["login"]


def vulnerabilities(org, repo):
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
              autoDismissedAt
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
        org=org,
        repo=repo,
    )


def prs(org, repo):
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
    return maybe_truncate(
        _client().graphql_query(
            query,
            path=["organization", "repository", "pullRequests"],
            org=org,
            repo=repo,
        )
    )


def issues(org, repo):
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
            org=org,
            repo=repo,
        )
    )


def codespaces(org):
    yield from _client().rest_query("/orgs/{org}/codespaces", org=org)


def _client():
    return GitHubClient(
        tokens={
            "ebmdatalab": os.environ["GITHUB_EBMDATALAB_TOKEN"],
            "opensafely-core": os.environ["GITHUB_OS_CORE_TOKEN"],
            "opensafely": os.environ["GITHUB_OS_TOKEN"],
        }
    )


def maybe_truncate(it):
    if "DEBUG_FAST" in os.environ:
        return itertools.islice(it, 5)
    return it
