from collections import defaultdict
from datetime import date, datetime, time, timedelta

import structlog

from metrics.github import query
from metrics.tools.dates import iter_days, next_weekday


log = structlog.get_logger()


def get_metrics(client, orgs):
    prs = get_prs(client, orgs)
    log.info(
        f"Got {sum(len(ps) for ps in prs.values())} PRs from {len(prs.keys())} repos"
    )

    old_counts = calculate_counts(prs, is_old)
    throughput_counts = calculate_counts(prs, was_merged_in_week_ending)

    count_metrics = convert_to_metrics(old_counts, "queue_older_than_7_days")
    throughput_metrics = convert_to_metrics(throughput_counts, "prs_merged")

    return count_metrics + throughput_metrics


def get_prs(client, orgs):
    prs = {}
    for org in orgs:
        for repo in query.repos(client, org):
            prs[repo] = list(query.prs(client, repo))
    return prs


def calculate_counts(prs_by_repo, predicate):
    counts = defaultdict(int)
    for repo, prs in prs_by_repo.items():
        start = next_weekday(repo["created_on"], 0)  # Monday
        end = repo["archived_on"] if repo["archived_on"] else date.today()

        for pr in prs:
            for monday in iter_days(start, end, step=timedelta(weeks=1)):
                if predicate(pr, monday):
                    counts[(repo["org"], repo["name"], pr["author"], monday)] += 1
    return dict(counts)


def is_old(pr, dt):
    opened = pr["created_on"]
    closed = pr["closed_on"] if pr["closed_on"] else None

    is_closed = closed and closed <= dt
    opened_more_than_a_week_ago = dt - opened >= timedelta(weeks=1)

    return not is_closed and opened_more_than_a_week_ago


def was_merged_in_week_ending(pr, dt):
    return pr["merged_on"] and dt - timedelta(weeks=1) < pr["merged_on"] <= dt


def convert_to_metrics(counts, name):
    metrics = []
    for coord, count in counts.items():
        org, repo, author, date_ = coord
        timestamp = datetime.combine(date_, time())
        metrics.append(
            {
                "name": name,
                "time": timestamp,
                "organisation": org,
                "repo": repo,
                "author": author,
                "value": count,
            }
        )
    return metrics
