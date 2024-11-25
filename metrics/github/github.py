import datetime
from dataclasses import dataclass

from metrics.github import query
from metrics.tools.dates import date_from_iso, datetime_from_iso


# Slugs (not names!) of the GitHub entities we're interested in
_TECH_TEAMS = ["team-rap", "team-rex", "tech-shared"]
_ORGS = ["ebmdatalab", "opensafely-core"]
# Some repos (for example the websites) frequently have PRs created by people
# outside the tech teams. We don't want our delivery metrics to be skewed by these
# and we don't necessarily want to hold people in other teams to the same hygiene
# standards as we hold ourselves. So we treat them differently. (We don't want to
# exclude such PRs from other repos because it's definitely interesting if there are
# old PRs (or lots of PRs) created by non-tech-team members in those repos.)
_CONTENT_REPOS = {
    "ebmdatalab": [
        "opensafely.org",
        "team-manual",
        "bennett.ox.ac.uk",
        "openprescribing",
    ]
}
_MANAGERS = {"sebbacon", "benbc"}
_EX_DEVELOPERS = {"ghickman", "milanwiedemann", "CarolineMorton"}


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

    @property
    def is_content_repo(self):
        return self.org in _CONTENT_REPOS and self.name in _CONTENT_REPOS[self.org]

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
    created_on: datetime.datetime
    merged_on: datetime.datetime
    closed_on: datetime.datetime
    is_draft: bool
    is_content: bool

    def age_on(self, date):
        return (date - self.created_on) / datetime.timedelta(days=1)

    def age_when_closed(self):
        if not self.was_closed():
            raise ValueError()
        return self.age_on(self.closed_on)

    def age_when_merged(self):
        if not self.was_merged():
            raise ValueError()
        return self.age_on(self.merged_on)

    def was_closed_on(self, date):
        return self.closed_on and self.closed_on <= date

    def was_merged_on(self, date):
        return self.merged_on and date == self.merged_on

    def was_open_at_end_of(self, date):
        return self.created_on <= date and not self.was_closed_on(date)

    def was_closed(self):
        return self.closed_on

    def was_merged(self):
        return self.merged_on

    def was_abandoned(self):
        return self.was_closed() and not self.was_merged()

    def was_opened_in_period(self, start_exclusive, end_inclusive):
        return start_exclusive < self.created_on <= end_inclusive

    def was_old_on(self, date):
        return not self.was_closed_on(date) and self.age_on(date) >= 7

    @classmethod
    def from_dict(cls, data, repo, tech_team_members):
        author = data["author"]["login"]
        is_content = repo.is_content_repo and author not in tech_team_members

        return cls(
            repo,
            author,
            datetime_from_iso(data["createdAt"]),
            datetime_from_iso(data["mergedAt"]),
            datetime_from_iso(data["closedAt"]),
            data["isDraft"],
            is_content,
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


@dataclass(frozen=True)
class Codespace:
    org: str
    repo_name: str
    user: str
    created_at: datetime.datetime
    last_used_at: datetime.datetime

    @classmethod
    def from_dict(cls, data, org):
        return cls(
            org=org,
            repo_name=data["repository"]["name"],
            user=data["owner"]["login"],
            created_at=data["created_at"],
            last_used_at=data["last_used_at"],
        )


def codespaces(org):
    return [
        Codespace.from_dict(data=codespace, org=org)
        for codespace in query.codespaces(org)
    ]


def tech_prs():
    tech_team_members = _tech_team_members()
    return [
        PR.from_dict(pr, repo, tech_team_members)
        for repo in tech_repos()
        for pr in query.prs(repo.org, repo.name)
    ]


def tech_issues():
    return [
        Issue.from_dict(i, repo)
        for repo in tech_repos()
        for i in query.issues(repo.org, repo.name)
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


def _tech_team_members():
    return (
        _MANAGERS
        | _EX_DEVELOPERS
        | {
            person
            for org in _ORGS
            for team in _TECH_TEAMS
            for person in query.team_members(org, team)
        }
    )
