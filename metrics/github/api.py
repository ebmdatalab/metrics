import json
import os
import textwrap
from datetime import date

import requests
import structlog

from ..tools.dates import date_from_iso


log = structlog.get_logger()

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]


session = requests.Session()
session.headers = {
    "Authorization": f"bearer {GITHUB_TOKEN}",
    "User-Agent": "Bennett Metrics",
}


def _get_query_page(*, query, session, cursor, **kwargs):
    """
    Get a page of the given query

    This uses the GraphQL API to avoid making O(N) calls to GitHub's (v3) REST
    API.  The passed cursor is a GraphQL cursor [1] allowing us to call this
    function in a loop, passing in the responses cursor to advance our view of
    the data.

    [1]: https://graphql.org/learn/pagination/#end-of-list-counts-and-connections
    """
    # use GraphQL variables to avoid string interpolation
    variables = {"cursor": cursor, **kwargs}
    payload = {"query": query, "variables": variables}

    log.debug(query=query, **variables)
    r = session.post("https://api.github.com/graphql", json=payload)

    if not r.ok:  # pragma: no cover
        print(r.headers)
        print(r.content)

    r.raise_for_status()
    results = r.json()

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

    return results["data"]["search"]


def _iter_query_results(query, **kwargs):
    """
    Get results from a GraphQL query

    Given a GraphQL query, return all results across one or more pages as a
    single generator.  We currently assume all results live under

        data.organization.team.repositories

    GitHub's GraphQL API provides cursor-based pagination, so this function
    wraps the actual API calls done in _get_query_page and tracks the cursor.
    one.
    """
    cursor = None
    while True:
        data = _get_query_page(
            query=query,
            session=session,
            cursor=cursor,
            **kwargs,
        )

        for edge in data["edges"]:
            yield edge["node"]

        if not data["pageInfo"]["hasNextPage"]:
            break

        # update the cursor we pass into the GraphQL query
        cursor = data["pageInfo"]["endCursor"]  # pragma: no cover


def _iter_pull_requests(org, date_range):
    # we can't seem to interpolate graphql variables into a string, so doing it
    # here
    search_query = f"is:pr draft:false org:{org} {date_range}"
    log.debug(f"GitHub search query: {search_query}")

    query = """
    query getPRs($cursor: String, $searchQuery: String!){
      search(query: $searchQuery, type:ISSUE, first: 100, after: $cursor) {
        edges {
          node {
            ... on PullRequest {
              createdAt
              closedAt
              mergedAt
              author {
                login
              }
              repository {
                name
                owner {
                  login
                }
                archivedAt
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

    """
    results = list(_iter_query_results(query, searchQuery=search_query))
    for pr in results:
        yield {
            "created": date_from_iso(pr["createdAt"]),
            "closed": date_from_iso(pr["closedAt"]),
            "merged": date_from_iso(pr["mergedAt"]),
            "author": pr["author"]["login"],
            "repo": pr["repository"]["name"],
            "repo_archived_at": date_from_iso(pr["repository"]["archivedAt"]),
            "org": pr["repository"]["owner"]["login"],
        }


def prs_open_in_range(org, start, end):
    start = start.isoformat()
    end = end.isoformat()
    date_range = f"created:<={start} closed:>={end}"

    return list(_iter_pull_requests(org, date_range))


def prs_merged_on_date(org, date):
    query = f"merged:{date}"

    return list(_iter_pull_requests(org, query))


def prs_opened_on_date(org, date):
    query = f"created:{date}"

    return list(_iter_pull_requests(org, query))


if __name__ == "__main__":
    orgs = ["ebmdatalab", "opensafely-core"]
    for pr in list(_iter_pull_requests(orgs[1], date(2023, 10, 24))):
        print(pr)
