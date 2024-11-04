import datetime
from collections import defaultdict

from metrics.github.github import PR
from metrics.tools.dates import iter_days


def get_pr_metrics(prs):
    old_counts = calculate_pr_counts(prs, PR.was_old_on)
    throughput_counts = calculate_pr_counts(prs, PR.was_merged_on)

    count_metrics = convert_pr_counts_to_metrics(old_counts, "queue_older_than_7_days")
    throughput_metrics = convert_pr_counts_to_metrics(throughput_counts, "prs_merged")

    return count_metrics + throughput_metrics


def calculate_pr_counts(prs, predicate):
    counts = defaultdict(int)
    for pr in prs:
        start = pr.created_on
        end = pr.closed_on if pr.closed_on else datetime.date.today()
        for day in iter_days(start, end):
            if predicate(pr, day):
                counts[(pr.repo.org, pr.repo.name, pr.author, pr.is_content, day)] += 1
    return dict(counts)


def convert_pr_counts_to_metrics(counts, name):
    metrics = []
    for coord, count in counts.items():
        org, repo, author, is_content, date_ = coord
        timestamp = datetime.datetime.combine(date_, datetime.time())
        metrics.append(
            {
                "name": name,
                "time": timestamp,
                "organisation": org,
                "repo": repo,
                "author": author,
                "is_content": is_content,
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


def convert_codespaces_to_dicts(codespaces):
    return [
        {
            "organisation": c.org,
            "repo": c.repo_name,
            "user": c.user,
            "created_at": c.created_at,
            "last_used_at": c.last_used_at,
            "has_uncommitted_changes": c.has_uncommitted_changes,
            "has_unpushed_changes": c.has_unpushed_changes,
            "deleted": c.deleted,
        }
        for c in codespaces
    ]
