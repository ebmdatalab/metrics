from dataclasses import dataclass
from datetime import date

from metrics.github import query
from metrics.tools.dates import date_from_iso


@dataclass(frozen=True)
class Repo:
    org: str
    name: str
    created_on: date
    is_archived: bool = False
    has_vulnerability_alerts_enabled: bool = False

    @classmethod
    def from_dict(cls, data, org):
        return cls(
            org,
            data["name"],
            date_from_iso(data["createdAt"]),
            data["archivedAt"] is not None,
            data["hasVulnerabilityAlertsEnabled"],
        )


def tech_repos(client, org):
    repo_names = []
    for team in _TECH_TEAMS:
        repo_names.extend(query.team_repos(client, org, team))

    return [r for r in _active_repos(client, org) if r.name in repo_names]


def get_repo_ownership(client, orgs):
    repo_owners = []

    for org in orgs:
        ownership = {}
        for team in _TECH_TEAMS:
            for repo in query.team_repos(client, org, team):
                ownership[repo] = team

        for repo in _active_repos(client, org):
            if repo.name in ownership:
                team = ownership[repo.name]
            else:
                team = None
            repo_owners.append({"organisation": org, "repo": repo.name, "owner": team})

    return repo_owners


def _active_repos(client, org):
    return [repo for repo in _all_repos(client, org) if not repo.is_archived]


def _all_repos(client, org):
    repos = query.repos(client, org)
    return [Repo.from_dict(r, org) for r in repos]


# GitHub slugs for the teams we're interested in
_TECH_TEAMS = ["team-rap", "team-rex", "tech-shared"]
