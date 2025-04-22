import datetime
from dataclasses import dataclass

from ..tools import dates
from . import github, query


@dataclass
class Vulnerability:
    created_on: datetime.date
    fixed_on: datetime.date | None
    dismissed_on: datetime.date | None
    auto_dismissed_on: datetime.date | None

    def is_open_on(self, target_date):
        return self.created_on <= target_date and not self.is_closed_on(target_date)

    def is_closed_on(self, target_date):
        return (
            (self.fixed_on is not None and self.fixed_on <= target_date)
            or (self.dismissed_on is not None and self.dismissed_on <= target_date)
            or (
                self.auto_dismissed_on is not None
                and self.auto_dismissed_on <= target_date
            )
        )

    @staticmethod
    def from_dict(my_dict):
        return Vulnerability(
            dates.date_from_iso(my_dict["createdAt"]),
            dates.date_from_iso(my_dict["fixedAt"]),
            dates.date_from_iso(my_dict["dismissedAt"]),
            dates.date_from_iso(my_dict["autoDismissedAt"]),
        )


def vulnerabilities(to_date):
    metrics = []

    for repo in github.tech_repos():
        vulns = list(
            map(Vulnerability.from_dict, query.vulnerabilities(repo.org, repo.name))
        )

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
