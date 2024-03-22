import datetime
from collections import defaultdict

import structlog

from metrics.github import query, repos
from metrics.tools.dates import iter_days


log = structlog.get_logger()


def get_metrics(client, orgs):
    issues = get_issues(client, orgs)
    log.info(f"Got {len(issues)} issues")

    counts = calculate_counts(issues)
    count_metrics = convert_to_metrics(counts)

    return count_metrics


def get_issues(client, orgs):
    issues = []
    for org in orgs:
        for repo in repos.tech_repos(client, org):
            issues.extend(query.issues(client, repo))
    return issues


def calculate_counts(issues):
    counts = defaultdict(int)
    for issue in issues:
        start = issue.created_on
        end = issue.closed_on if issue.closed_on else datetime.date.today()
        for day in iter_days(start, end):
            counts[(issue.repo.org, issue.repo.name, issue.author, day)] += 1
    return dict(counts)


def convert_to_metrics(counts):
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
