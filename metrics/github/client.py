import json
import re
import textwrap
from urllib.parse import urljoin

import requests
import structlog


log = structlog.get_logger()


session = requests.Session()


class GitHubRestClient:
    def __init__(self, org, token):
        self.org = org
        self.token = token

    def get(self, path):
        session.headers = {
            "Authorization": f"bearer {self.token}",
            "User-Agent": "Bennett Metrics",
        }
        base_url = "https://api.github.com"
        full_url = urljoin(base_url, path)
        response = session.get(full_url)

        if not response.ok:
            log.info(response.headers)
            log.info(response.content)

        response.raise_for_status()
        return response

    def get_paged_results(self, path, start_date="", per_page=100):
        full_path = f"{path}?per_page={per_page}&since={start_date}"
        while full_path:
            response = self.get(full_path)
            yield response.json()
            full_path = self.get_next_page_url(response.headers)

    def get_next_page_url(self, headers):
        link_header = headers.get("Link", "")
        next_link_match = re.search(r'<([^>]+)>;\s*rel="next"', link_header)
        return next_link_match.group(1) if next_link_match else None


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
