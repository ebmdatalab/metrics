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


def tech_prs(client, orgs):
    prs = {}
    for org in orgs:
        for repo in tech_repos(client, org):
            prs[repo] = list(query.prs(client, repo))
    return prs


def tech_repos(client, org):
    return [r for r in _active_repos(client, org) if r.is_tech_owned]


def all_repos(client, org):
    return _active_repos(client, org)


def _active_repos(client, org):
    return [repo for repo in _get_repos(client, org) if not repo.is_archived]


def _get_repos(client, org):
    ownership = _repo_owners(client, org)
    repos = []
    for repo in query.repos(client, org):
        owner = ownership.get(repo["name"])
        repos.append(Repo.from_dict(repo, org, owner))
    return repos


def _repo_owners(client, org):
    ownership = {}
    for team in _TECH_TEAMS:
        for repo in query.team_repos(client, org, team):
            ownership[repo] = team
    return ownership


# GitHub slugs for the teams we're interested in
_TECH_TEAMS = ["team-rap", "team-rex", "tech-shared"]
