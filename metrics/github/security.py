from dataclasses import dataclass
from datetime import date

from metrics.github.repos import tech_owned_repo

from ..tools import dates
from . import query


@dataclass
class Vulnerability:
    created_at: date
    fixed_at: date | None
    dismissed_at: date | None

    def is_open_at(self, target_date):
        return self.created_at <= target_date and not self.is_closed_at(target_date)

    def is_closed_at(self, target_date):
        return (self.fixed_at is not None and self.fixed_at <= target_date) or (
            self.dismissed_at is not None and self.dismissed_at <= target_date
        )

    @staticmethod
    def from_dict(my_dict):
        return Vulnerability(
            dates.date_from_iso(my_dict["createdAt"]),
            dates.date_from_iso(my_dict["fixedAt"]),
            dates.date_from_iso(my_dict["dismissedAt"]),
        )


@dataclass
class Repo:
    name: str
    org: str
    vulnerabilities: list[Vulnerability]

    def __post_init__(self):
        self.vulnerabilities.sort(key=lambda v: v.created_at)

    def earliest_date(self):
        return self.vulnerabilities[0].created_at


def get_repos(client):
    for repo in query.repos(client):
        if repo["archived_at"] or not tech_owned_repo(repo):
            continue

        vulnerabilities = []
        for vuln in query.vulnerabilities(client, repo):
            vulnerabilities.append(Vulnerability.from_dict(vuln))

        if vulnerabilities:
            yield Repo(repo["name"], client.org, vulnerabilities)


def vulnerabilities(client, to_date):
    for repo in get_repos(client):
        for day in dates.iter_days(repo.earliest_date(), to_date):
            closed_vulns = sum(1 for v in repo.vulnerabilities if v.is_closed_at(day))
            open_vulns = sum(1 for v in repo.vulnerabilities if v.is_open_at(day))

            yield {
                "time": day,
                "closed": closed_vulns,
                "open": open_vulns,
                "organisation": repo.org,
                "repo": repo.name,
                "value": 0,  # needed for the timescaledb
            }
