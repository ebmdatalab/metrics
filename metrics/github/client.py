import json
import textwrap

import requests
import structlog


log = structlog.get_logger()


session = requests.Session()


class GitHubClient:
    def __init__(self, token=None, tokens=None):
        assert token or tokens
        assert not (token and tokens)
        self.token = token
        self.tokens = tokens

    def graphql_query(self, query, path, **kwargs):
        def extract(data):
            result = data
            for key in path:
                try:
                    result = result[key]
                except TypeError:
                    raise Exception(f"Couldn't find {path} in {data}")
            return result

        more_pages = True
        cursor = None
        while more_pages:
            page = extract(
                self.graphql_query_page(query=query, cursor=cursor, **kwargs)
            )
            yield from page["nodes"]
            more_pages = page["pageInfo"]["hasNextPage"]
            cursor = page["pageInfo"]["endCursor"]

    def graphql_query_page(self, query, cursor, **kwargs):
        """
        Get a page of the given query

        This uses the GraphQL API to avoid making O(N) calls to GitHub's (v3) REST
        API.  The passed cursor is a GraphQL cursor [1] allowing us to call this
        function in a loop, passing in the responses cursor to advance our view of
        the data.

        [1]: https://graphql.org/learn/pagination/#end-of-list-counts-and-connections
        """
        variables = {"cursor": cursor, **kwargs}
        headers = self._get_headers(variables)
        response = session.post(
            "https://api.github.com/graphql",
            headers=headers,
            json={"query": query, "variables": variables},
        )

        check_response(response)
        results = response.json()

        if (
            "data" not in results
            or not results["data"]
            or ("errors" in results and results["errors"])
        ):
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

    def _get_headers(self, variables):
        if self.token:
            token = self.token
        else:
            token = self.tokens[variables["org"]]
        headers = {
            "Authorization": f"bearer {token}",
            "User-Agent": "Bennett Metrics",
        }
        return headers


def check_response(response):
    if not response.ok:
        log.info(response.headers)
        log.info(response.content)
    response.raise_for_status()
