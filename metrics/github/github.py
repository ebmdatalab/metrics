import datetime
from dataclasses import dataclass

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
    created_on: datetime.date
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


@dataclass(frozen=True)
class PR:
    repo: Repo
    author: str
    created_on: datetime.date
    merged_on: datetime.date
    closed_on: datetime.date

    def was_old_on(self, date):
        opened = self.created_on
        closed = self.closed_on if self.closed_on else None

        is_closed = closed and closed <= date
        opened_more_than_a_week_ago = date - opened >= datetime.timedelta(weeks=1)

        return not is_closed and opened_more_than_a_week_ago

    def was_merged_on(self, date):
        return self.merged_on and date == self.merged_on

    @classmethod
    def from_dict(cls, data, repo):
        return cls(
            repo,
            data["author"]["login"],
            date_from_iso(data["createdAt"]),
            date_from_iso(data["mergedAt"]),
            date_from_iso(data["closedAt"]),
        )


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


def tech_prs():
    return [PR.from_dict(pr, repo) for repo in tech_repos() for pr in query.prs(repo)]


def tech_issues():
    return [
        Issue.from_dict(i, repo) for repo in tech_repos() for i in query.issues(repo)
    ]


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
    return {repo: team for team in _TECH_TEAMS for repo in query.team_repos(org, team)}
