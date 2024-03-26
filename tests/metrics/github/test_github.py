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
            },
            "ebmdatalab": {
                "team-rap": [],
                "team-rex": [],
                "tech-shared": [],
            },
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
    assert len(github.tech_repos()) == 4


def test_excludes_non_tech_owned_repos(patch):
    patch(
        "team_repos",
        {
            "opensafely-core": {"team-rap": [], "team-rex": [], "tech-shared": []},
            "ebmdatalab": {"team-rap": [], "team-rex": [], "tech-shared": []},
        },
    )
    patch(
        "repos",
        [
            repo_data("other-repo"),
        ],
    )
    assert len(github.tech_repos()) == 0


def test_excludes_archived_tech_repos(patch):
    patch(
        "team_repos",
        {
            "opensafely-core": {
                "team-rap": ["other-repo"],
                "team-rex": [],
                "tech-shared": [],
            },
            "ebmdatalab": {"team-rap": [], "team-rex": [], "tech-shared": []},
        },
    )
    patch(
        "repos",
        [
            repo_data("other-repo", is_archived=True),
        ],
    )
    assert len(github.tech_repos()) == 0


def test_looks_up_ownership(patch):
    patch(
        "repos",
        {
            "ebmdatalab": [repo_data("repo1"), repo_data("repo2"), repo_data("repo3")],
            "opensafely-core": [],
        },
    )
    patch(
        "team_repos",
        {
            "ebmdatalab": {
                "team-rex": ["repo1"],
                "team-rap": ["repo2"],
                "tech-shared": ["repo3"],
            },
            "opensafely-core": {"team-rap": [], "team-rex": [], "tech-shared": []},
        },
    )
    assert github.all_repos() == [
        repo("ebmdatalab", "repo1", "team-rex"),
        repo("ebmdatalab", "repo2", "team-rap"),
        repo("ebmdatalab", "repo3", "tech-shared"),
    ]


def test_excludes_archived_non_tech_repos(patch):
    patch("repos", [repo_data("the_repo", is_archived=True)])
    patch(
        "team_repos",
        {
            "ebmdatalab": {"team-rex": [], "team-rap": [], "tech-shared": []},
            "opensafely-core": {"team-rap": [], "team-rex": [], "tech-shared": []},
        },
    )
    assert github.all_repos() == []


def test_returns_none_for_unknown_ownership(patch):
    patch("repos", {"ebmdatalab": [repo_data("the_repo")], "opensafely-core": []})
    patch(
        "team_repos",
        {
            "ebmdatalab": {"team-rex": [], "team-rap": [], "tech-shared": []},
            "opensafely-core": {"team-rap": [], "team-rex": [], "tech-shared": []},
        },
    )
    assert github.all_repos() == [repo("ebmdatalab", "the_repo", None)]


def repo_data(name, is_archived=False):
    return dict(
        name=name,
        createdAt=datetime.datetime.min.isoformat(),
        archivedAt=datetime.datetime.now().isoformat() if is_archived else None,
        hasVulnerabilityAlertsEnabled=False,
    )


def repo(org, name, team):
    return Repo(org, name, team, datetime.date.min)
