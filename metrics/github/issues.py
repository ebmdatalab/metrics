import datetime
from collections import defaultdict
from dataclasses import dataclass

import structlog

from metrics.github import query, repos
from metrics.github.repos import Repo
from metrics.tools.dates import date_from_iso, iter_days


log = structlog.get_logger()


@dataclass(frozen=True)
class Issue:
    repo: Repo
    author: str
    created_on: datetime.date
    closed_on: datetime.date

    @classmethod
    def from_dict(cls, data, repo):
        return cls(
            repo,
            data["author"]["login"],
            date_from_iso(data["createdAt"]),
            date_from_iso(data["closedAt"]),
        )


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
            issues.extend(Issue.from_dict(i, repo) for i in query.issues(client, repo))
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
