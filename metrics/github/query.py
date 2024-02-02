from metrics.github.repos import tech_owned_repo
from metrics.tools.dates import date_from_iso


# We want to use some of these objects as keys in dicts. This is a pretty half-hearted
# implementation, but it does as much as we need.
class FrozenDict:
    def __init__(self, dict_):
        self._dict = dict_

    def __getitem__(self, key):
        return self._dict[key]

    def __hash__(self):
        return hash(tuple(self._dict.items()))


def repos(client, org):
    query = """
    query repos($cursor: String, $org: String!) {
      organization(login: $org) {
        repositories(first: 100, after: $cursor) {
          nodes {
            name
            createdAt
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
        repo = FrozenDict(
            {
                "org": org,
                "name": raw_repo["name"],
                "created_on": date_from_iso(raw_repo["createdAt"]),
                "archived_on": date_from_iso(raw_repo["archivedAt"]),
            }
        )
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
            "author": pr["author"]["login"],
            "closed_on": date_from_iso(pr["closedAt"]),
            "created_on": date_from_iso(pr["createdAt"]),
            "merged_on": date_from_iso(pr["mergedAt"]),
        }
