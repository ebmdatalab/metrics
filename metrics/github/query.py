from metrics.tools.dates import datetime_from_iso


def reactions(client):
    query = """
    query reactions($cursor: String) {
      repository(owner: "ebmdatalab", name: "opensafely-output-review") {
        issues(first: 100, after: $cursor) {
          nodes {
            number
            reactions(first: 100) {
              nodes {
                content
                createdAt
                user {
                  login
                }
              }
            }
          }
          pageInfo {
            endCursor
            hasNextPage
          }
        }
      }
    }
    """
    for issue in client.get_query(query, path=["repository", "issues"]):
        for reaction in issue["reactions"]["nodes"]:
            # issue -> {'reactions': {'nodes': [{'content': 'EYES', 'user': {'login': 'milanwiedemann'}}]}}
            # OR
            # issue -> {'reactions': {'nodes': []}}

            # get_query turns issues into an iterator for us, but we can't dig
            # below that with get_query so we need to do some generator "magic"
            # here to flatten the data into the shape we want at the call site

            # TODO: yield out the data needed here
            # FIXME: probably also need issue number
            yield {
                "number": issue["number"],
                "type": reaction["content"],
                "user": reaction["user"]["login"],
                "created_at": datetime_from_iso(reaction["createdAt"]),
            }


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
            "archived_at": repo["archivedAt"],
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
            "repo_archived_at": datetime_from_iso(repo["archived_at"]),
            "author": pr["author"]["login"],
            "closed_at": datetime_from_iso(pr["closedAt"]),
            "created_at": datetime_from_iso(pr["createdAt"]),
            "merged_at": datetime_from_iso(pr["mergedAt"]),
        }
