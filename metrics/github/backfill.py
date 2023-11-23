import json
import textwrap
from datetime import date, timedelta

import click
import structlog

from ..logs import setup_logging
from ..timescaledb import TimescaleDBWriter
from ..timescaledb.tables import GitHubPullRequests
from ..tools.dates import date_from_iso, iter_days, previous_weekday
from .api import session
from .prs import process_prs


setup_logging()

log = structlog.get_logger()


def get_query_page(*, query, session, cursor, **kwargs):
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

    return results["data"]


def get_query(query, path, **kwargs):
    def extract(data):
        result = data
        for key in path:
            result = result[key]
        return result

    more_pages = True
    cursor = None
    while more_pages:
        page = extract(
            get_query_page(query=query, session=session, cursor=cursor, **kwargs)
        )
        yield from page["nodes"]
        more_pages = page["pageInfo"]["hasNextPage"]
        cursor = page["pageInfo"]["endCursor"]


def iter_repos(org):
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
    for repo in get_query(query, path=["organization", "repositories"], org=org):
        yield {
            "name": repo["name"],
            "archived": repo["archivedAt"],
        }


def iter_repo_prs(org, repo):
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
    for pr in get_query(
        query,
        path=["organization", "repository", "pullRequests"],
        org=org,
        repo=repo["name"],
    ):
        yield {
            "org": org,
            "repo": repo["name"],
            "repo_archived_at": date_from_iso(repo["archived"]),
            "author": pr["author"]["login"],
            "created": date_from_iso(pr["createdAt"]),
            "closed": date_from_iso(pr["closedAt"]),
            "merged": date_from_iso(pr["mergedAt"]),
        }


def iter_prs(org):
    for r in iter_repos(org):
        yield from iter_repo_prs(org, r["name"])


def open_prs(prs, org, days_threshold):
    earliest = min([pr["created"] for pr in prs])
    start = previous_weekday(earliest, 0)  # Monday
    mondays = list(iter_days(start, date.today(), step=timedelta(days=7)))

    today = date.today()
    threshold = timedelta(days=days_threshold)

    def open_on_day(pr, start, end):
        """
        Filter function for PRs

        Checks whether a PR is open today and if it's been open for greater or
        equal to the threshold of days.
        """
        closed = pr["closed"] or today
        opened = pr["created"]

        open_today = (opened <= start) and (closed >= end)
        if not open_today:
            return False

        return (closed - opened) >= threshold

    with TimescaleDBWriter(GitHubPullRequests) as writer:
        for start in mondays:
            end = start + timedelta(days=6)
            prs_on_day = [pr for pr in prs if open_on_day(pr, start, end)]

            name = f"queue_older_than_{days_threshold}_days"

            log.info(
                "%s | %s | Processing %s PRs from week starting %s",
                name,
                org,
                len(prs_on_day),
                start,
            )
            process_prs(writer, prs_on_day, start, name=name)


def pr_throughput(prs, org):
    start = min([pr["created"] for pr in prs])
    days = list(iter_days(start, date.today()))

    with TimescaleDBWriter(GitHubPullRequests) as writer:
        for day in days:
            opened_prs = [pr for pr in prs if pr["created"] == day]
            log.info("%s | %s | Processing %s opened PRs", day, org, len(opened_prs))
            process_prs(writer, opened_prs, day, name="prs_opened")

            merged_prs = [pr for pr in prs if pr["merged"] and pr["merged"] == day]
            log.info("%s | %s | Processing %s merged PRs", day, org, len(merged_prs))
            process_prs(writer, merged_prs, day, name="prs_merged")


@click.command()
@click.argument("org")
@click.pass_context
def backfill(ctx, org):
    """Backfill GitHub data for the given GitHub ORG"""
    prs = list(iter_prs(org))

    org_prs = [pr for pr in prs if pr["org"] == org]
    log.info("Backfilling with %s PRs for %s", len(org_prs), org)

    open_prs(org_prs, org, days_threshold=7)
    pr_throughput(org_prs, org)
