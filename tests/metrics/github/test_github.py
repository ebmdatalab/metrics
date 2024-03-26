import datetime

import pytest

from metrics.github import github
from metrics.github.github import Repo


@pytest.fixture
def patch(monkeypatch):
    def patch(query_func, result):
        if isinstance(result, list):
            fake = lambda *_args: result
        elif isinstance(result, dict):

            def fake(*keys):
                r = result
                for key in keys:
                    r = r[key]
                return r

        else:
            raise ValueError
        monkeypatch.setattr(github.query, query_func, fake)

    return patch


def test_includes_tech_owned_repos(patch):
    patch(
        "team_repos",
        {
            "opensafely-core": {
                "team-rap": ["ehrql", "cohort-extractor"],
                "team-rex": ["job-server"],
                "tech-shared": [".github"],
            }
        },
    )
    patch(
        "repos",
        [
            repo_data("ehrql"),
            repo_data("cohort-extractor"),
            repo_data("job-server"),
            repo_data(".github"),
        ],
    )
    assert len(github.tech_repos("opensafely-core")) == 4


def test_excludes_non_tech_owned_repos(patch):
    patch(
        "team_repos",
        {"opensafely-core": {"team-rap": [], "team-rex": [], "tech-shared": []}},
    )
    patch(
        "repos",
        [
            repo_data("other-repo"),
        ],
    )
    assert len(github.tech_repos("opensafely-core")) == 0


def test_excludes_archived_tech_repos(patch):
    patch(
        "team_repos",
        {
            "opensafely-core": {
                "team-rap": ["other-repo"],
                "team-rex": [],
                "tech-shared": [],
            }
        },
    )
    patch(
        "repos",
        [
            repo_data("other-repo", is_archived=True),
        ],
    )
    assert len(github.tech_repos("opensafely-core")) == 0


def test_looks_up_ownership(patch):
    patch(
        "repos",
        [repo_data("repo1"), repo_data("repo2"), repo_data("repo3")],
    )
    patch(
        "team_repos",
        {
            "the_org": {
                "team-rex": ["repo1"],
                "team-rap": ["repo2"],
                "tech-shared": ["repo3"],
            }
        },
    )
    assert github.all_repos("the_org") == [
        repo("the_org", "repo1", "team-rex"),
        repo("the_org", "repo2", "team-rap"),
        repo("the_org", "repo3", "tech-shared"),
    ]


def test_excludes_archived_non_tech_repos(patch):
    patch("repos", [repo_data("the_repo", is_archived=True)])
    patch(
        "team_repos",
        {"the_org": {"team-rex": [], "team-rap": [], "tech-shared": []}},
    )
    assert github.all_repos("the_org") == []


def test_returns_none_for_unknown_ownership(patch):
    patch("repos", [repo_data("the_repo")])
    patch(
        "team_repos", {"the_org": {"team-rex": [], "team-rap": [], "tech-shared": []}}
    )
    assert github.all_repos("the_org") == [repo("the_org", "the_repo", None)]


def repo_data(name, is_archived=False):
    return dict(
        name=name,
        createdAt=datetime.datetime.min.isoformat(),
        archivedAt=datetime.datetime.now().isoformat() if is_archived else None,
        hasVulnerabilityAlertsEnabled=False,
    )


def repo(org, name, team):
    return Repo(org, name, team, datetime.date.min)
