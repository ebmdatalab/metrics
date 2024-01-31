from metrics.github.repos import tech_owned_repo
from metrics.tools.dates import datetime_from_iso


def repos(client, org):
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
    for raw_repo in client.get_query(
        query, path=["organization", "repositories"], org=org
    ):
        repo = {
            "org": org,
            "name": raw_repo["name"],
            "archived_at": datetime_from_iso(raw_repo["archivedAt"]),
        }
        if tech_owned_repo(repo):
            yield repo


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
        org=repo["org"],
        repo=repo["name"],
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
    for pr in client.get_query(
        query,
        path=["organization", "repository", "pullRequests"],
        org=repo["org"],
        repo=repo["name"],
    ):
        yield {
            "org": repo["org"],
            "repo": repo["name"],
            "repo_archived_at": repo["archived_at"],
            "author": pr["author"]["login"],
            "closed_at": datetime_from_iso(pr["closedAt"]),
            "created_at": datetime_from_iso(pr["createdAt"]),
            "merged_at": datetime_from_iso(pr["mergedAt"]),
        }
