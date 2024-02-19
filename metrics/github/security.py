from dataclasses import dataclass
from datetime import date

from ..tools import dates
from . import query


@dataclass
class Vulnerability:
    created_on: date
    fixed_on: date | None
    dismissed_on: date | None

    def is_open_on(self, target_date):
        return self.created_on <= target_date and not self.is_closed_on(target_date)

    def is_closed_on(self, target_date):
        return (self.fixed_on is not None and self.fixed_on <= target_date) or (
            self.dismissed_on is not None and self.dismissed_on <= target_date
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
        self.vulnerabilities.sort(key=lambda v: v.created_on)

    def earliest_date(self):
        return self.vulnerabilities[0].created_on


def get_repos(client, org):
    for repo in query.repos(client, org):
        if repo["archived_on"]:
            continue

        vulnerabilities = []
        for vuln in query.vulnerabilities(client, repo):
            vulnerabilities.append(Vulnerability.from_dict(vuln))

        if vulnerabilities:
            yield Repo(repo["name"], repo["org"], vulnerabilities)


def vulnerabilities(client, org, to_date):
    for repo in get_repos(client, org):
        for day in dates.iter_days(repo.earliest_date(), to_date):
            closed_vulns = sum(1 for v in repo.vulnerabilities if v.is_closed_on(day))
            open_vulns = sum(1 for v in repo.vulnerabilities if v.is_open_on(day))

            yield {
                "time": day,
                "closed": closed_vulns,
                "open": open_vulns,
                "organisation": repo.org,
                "repo": repo.name,
                "value": 0,  # needed for the timescaledb
            }
