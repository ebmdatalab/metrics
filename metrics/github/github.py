from dataclasses import dataclass
from datetime import date

from metrics.github import query
from metrics.tools.dates import date_from_iso


@dataclass(frozen=True)
class Repo:
    org: str
    name: str
    team: str
    created_on: date
    is_archived: bool = False
    has_vulnerability_alerts_enabled: bool = False

    @property
    def is_tech_owned(self):
        return self.team in _TECH_TEAMS

    @classmethod
    def from_dict(cls, data, org, team):
        return cls(
            org,
            data["name"],
            team,
            date_from_iso(data["createdAt"]),
            data["archivedAt"] is not None,
            data["hasVulnerabilityAlertsEnabled"],
        )


def tech_prs(orgs):
    prs = {}
    for org in orgs:
        for repo in tech_repos(org):
            prs[repo] = list(query.prs(repo))
    return prs


def tech_repos(org):
    return [r for r in _active_repos(org) if r.is_tech_owned]


def all_repos(org):
    return _active_repos(org)


def _active_repos(org):
    return [repo for repo in _get_repos(org) if not repo.is_archived]


def _get_repos(org):
    ownership = _repo_owners(org)
    repos = []
    for repo in query.repos(org):
        owner = ownership.get(repo["name"])
        repos.append(Repo.from_dict(repo, org, owner))
    return repos


def _repo_owners(org):
    ownership = {}
    for team in _TECH_TEAMS:
        for repo in query.team_repos(org, team):
            ownership[repo] = team
    return ownership


# GitHub slugs for the teams we're interested in
_TECH_TEAMS = ["team-rap", "team-rex", "tech-shared"]
