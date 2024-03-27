import datetime
from collections import defaultdict

from metrics.tools.dates import iter_days


def get_pr_metrics(prs):
    old_counts = calculate_pr_counts(prs, is_old)
    throughput_counts = calculate_pr_counts(prs, was_merged_on)

    count_metrics = convert_pr_counts_to_metrics(old_counts, "queue_older_than_7_days")
    throughput_metrics = convert_pr_counts_to_metrics(throughput_counts, "prs_merged")

    return count_metrics + throughput_metrics


def calculate_pr_counts(prs_by_repo, predicate):
    counts = defaultdict(int)
    for repo, prs in prs_by_repo.items():
        for pr in prs:
            start = pr.created_on
            end = pr.closed_on if pr.closed_on else datetime.date.today()
            for day in iter_days(start, end):
                if predicate(pr, day):
                    counts[(repo.org, repo.name, pr.author, day)] += 1
    return dict(counts)


def is_old(pr, dt):
    opened = pr.created_on
    closed = pr.closed_on if pr.closed_on else None

    is_closed = closed and closed <= dt
    opened_more_than_a_week_ago = dt - opened >= datetime.timedelta(weeks=1)

    return not is_closed and opened_more_than_a_week_ago


def was_merged_on(pr, dt):
    return pr.merged_on and dt == pr.merged_on


def convert_pr_counts_to_metrics(counts, name):
    metrics = []
    for coord, count in counts.items():
        org, repo, author, date_ = coord
        timestamp = datetime.datetime.combine(date_, datetime.time())
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


def get_issues_metrics(issues):
    counts = calculate_issue_counts(issues)
    return convert_issue_counts_to_metrics(counts)


def calculate_issue_counts(issues):
    counts = defaultdict(int)
    for issue in issues:
        start = issue.created_on
        end = issue.closed_on if issue.closed_on else datetime.date.today()
        for day in iter_days(start, end):
            counts[(issue.repo.org, issue.repo.name, issue.author, day)] += 1
    return dict(counts)


def convert_issue_counts_to_metrics(counts):
    metrics = []
    for coord, count in counts.items():
        org, repo, author, date = coord
        timestamp = datetime.datetime.combine(date, datetime.time())
        metrics.append(
            {
                "time": timestamp,
                "organisation": org,
                "repo": repo,
                "author": author,
                "count": count,
            }
        )
    return metrics
