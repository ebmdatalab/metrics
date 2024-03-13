from dataclasses import dataclass
from datetime import date

from ..tools import dates
from . import query, repos


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


def vulnerabilities(client, org, to_date):
    metrics = []

    for repo in repos.tech_repos(client, org):
        vulns = list(map(Vulnerability.from_dict, query.vulnerabilities(client, repo)))

        for day in dates.iter_days(repo.created_on, to_date):
            closed_vulns = sum(1 for v in vulns if v.is_closed_on(day))
            open_vulns = sum(1 for v in vulns if v.is_open_on(day))

            metrics.append(
                {
                    "time": day,
                    "closed": closed_vulns,
                    "open": open_vulns,
                    "organisation": repo.org,
                    "repo": repo.name,
                    "has_alerts_enabled": repo.has_vulnerability_alerts_enabled,
                    "value": 0,  # needed for the timescaledb
                }
            )

    return metrics
