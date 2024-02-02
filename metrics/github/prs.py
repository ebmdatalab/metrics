from collections import defaultdict
from datetime import date, datetime, time, timedelta

from metrics.github import query
from metrics.tools.dates import iter_days, next_weekday


def get_metrics(client, org):
    prs = get_prs(client, org)

    old_counts = calculate_counts(prs, is_old)
    throughput_counts = calculate_counts(prs, was_merged_in_week_ending)

    count_metrics = convert_to_metrics(old_counts, org, "queue_older_than_7_days")
    throughput_metrics = convert_to_metrics(throughput_counts, org, "prs_merged")

    return count_metrics + throughput_metrics


def get_prs(client, org):
    prs_by_repo = {}
    for repo in query.repos(client, org):
        prs_by_repo[repo] = list(query.prs(client, repo))
    return prs_by_repo


def calculate_counts(prs_by_repo, predicate):
    counts = defaultdict(int)
    for repo, prs in prs_by_repo.items():
        start = next_weekday(repo["created_at"].date(), 0)  # Monday
        end = repo["archived_at"].date() if repo["archived_at"] else date.today()

        for pr in prs:
            for monday in iter_days(start, end, step=timedelta(weeks=1)):
                if predicate(pr, monday):
                    counts[(repo["name"], pr["author"], monday)] += 1
    return dict(counts)


def is_old(pr, dt):
    opened = pr["created_at"].date()
    closed = pr["closed_at"].date() if pr["closed_at"] else None

    is_closed = closed and closed <= dt
    opened_more_than_a_week_ago = dt - opened >= timedelta(weeks=1)

    return not is_closed and opened_more_than_a_week_ago


def was_merged_in_week_ending(pr, dt):
    return pr["merged_at"] and dt - timedelta(weeks=1) < pr["merged_at"].date() <= dt


def convert_to_metrics(counts, org, name):
    metrics = []
    for coord, count in counts.items():
        repo, author, date_ = coord
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
