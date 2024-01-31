from metrics.tools.dates import datetime_from_iso


def repos(client):
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
    for repo in client.get_query(query, path=["organization", "repositories"]):
        yield {
            "org": client.org,
            "name": repo["name"],
            "archived_at": datetime_from_iso(repo["archivedAt"]),
        }


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
        org=client.org,
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
        repo=repo["name"],
    ):
        yield {
            "org": client.org,
            "repo": repo["name"],
            "repo_archived_at": repo["archived_at"],
            "author": pr["author"]["login"],
            "closed_at": datetime_from_iso(pr["closedAt"]),
            "created_at": datetime_from_iso(pr["createdAt"]),
            "merged_at": datetime_from_iso(pr["mergedAt"]),
        }
