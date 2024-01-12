import json
import textwrap

import requests
import structlog

from ..tools.dates import datetime_from_iso


log = structlog.get_logger()


session = requests.Session()


class GitHubClient:
    def __init__(self, org, token):
        self.org = org
        self.token = token

    def post(self, query, variables):
        session.headers = {
            "Authorization": f"bearer {self.token}",
            "User-Agent": "Bennett Metrics",
        }
        response = session.post(
            "https://api.github.com/graphql",
            json={"query": query, "variables": {"org": self.org, **variables}},
        )

        if not response.ok:
            log.info(response.headers)
            log.info(response.content)

        response.raise_for_status()
        return response.json()

    def get_query_page(self, query, cursor, **kwargs):
        """
        Get a page of the given query

        This uses the GraphQL API to avoid making O(N) calls to GitHub's (v3) REST
        API.  The passed cursor is a GraphQL cursor [1] allowing us to call this
        function in a loop, passing in the responses cursor to advance our view of
        the data.

        [1]: https://graphql.org/learn/pagination/#end-of-list-counts-and-connections
        """
        variables = {"cursor": cursor, **kwargs}
        results = self.post(query, variables)

        # In some cases graphql will return a 200 response when there are errors.
        # https://sachee.medium.com/200-ok-error-handling-in-graphql-7ec869aec9bc
        # Handling things robustly is complex and query specific, so here we simply
        # take the absence of 'data' as an error, rather than the presence of
        # 'errors' key.
        if "data" not in results:
            msg = textwrap.dedent(
                f"""
                graphql query failed

                query:
                {query}

                response:
                {json.dumps(results, indent=2)}
            """
            )
            raise RuntimeError(msg)

        return results["data"]

    def get_query(self, query, path, **kwargs):
        def extract(data):
            result = data
            for key in path:
                result = result[key]
            return result

        more_pages = True
        cursor = None
        while more_pages:
            page = extract(self.get_query_page(query=query, cursor=cursor, **kwargs))
            yield from page["nodes"]
            more_pages = page["pageInfo"]["hasNextPage"]
            cursor = page["pageInfo"]["endCursor"]


def iter_repos(client):
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
            "name": repo["name"],
            "archived_at": repo["archivedAt"],
        }


def iter_repo_prs(client, repo):
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
        org=client.org,
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
