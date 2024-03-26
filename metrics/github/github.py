from dataclasses import dataclass
from datetime import date

from metrics.github import query
from metrics.tools.dates import date_from_iso


# Slugs (not names!) of the GitHub entities we're interested in
_TECH_TEAMS = ["team-rap", "team-rex", "tech-shared"]
_ORGS = ["ebmdatalab", "opensafely-core"]


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


def tech_prs():
    return {repo: list(query.prs(repo)) for repo in tech_repos()}


def tech_repos():
    return [repo for repo in all_repos() if repo.is_tech_owned]


def all_repos():
    return [repo for repo in _get_repos() if not repo.is_archived]


def _get_repos():
    repos = []
    for org in _ORGS:
        ownership = _repo_owners(org)
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
