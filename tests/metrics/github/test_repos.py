from datetime import date

import pytest

from metrics.github import repos
from metrics.github.query import Repo


@pytest.fixture
def patch(monkeypatch):
    def patch(query_func, result):
        if isinstance(result, list):
            fake = lambda *_args: result
        elif isinstance(result, dict):

            def fake(_client, *keys):
                r = result
                for key in keys:
                    r = r[key]
                return r

        else:
            raise ValueError
        monkeypatch.setattr(repos.query, query_func, fake)

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
            repo("opensafely-core", "ehrql"),
            repo("opensafely-core", "cohort-extractor"),
            repo("opensafely-core", "job-server"),
            repo("opensafely-core", ".github"),
        ],
    )
    assert len(repos.tech_repos(None, "opensafely-core")) == 4


def test_excludes_non_tech_owned_repos(patch):
    patch(
        "team_repos",
        {"opensafely-core": {"team-rap": [], "team-rex": [], "tech-shared": []}},
    )
    patch(
        "repos",
        [
            repo("opensafely-core", "other-repo"),
        ],
    )
    assert len(repos.tech_repos(None, "opensafely-core")) == 0


def test_excludes_archived_repos(patch):
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
            repo("opensafely-core", "other-repo", archived_on=date.min),
        ],
    )
    assert len(repos.tech_repos(None, "opensafely-core")) == 0


def test_looks_up_ownership(patch):
    patch(
        "repos",
        [repo("the_org", "repo1"), repo("the_org", "repo2"), repo("the_org", "repo3")],
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
    assert repos.get_repo_ownership(None, ["the_org"]) == [
        {"organisation": "the_org", "repo": "repo1", "owner": "team-rex"},
        {"organisation": "the_org", "repo": "repo2", "owner": "team-rap"},
        {"organisation": "the_org", "repo": "repo3", "owner": "tech-shared"},
    ]


def test_looks_up_ownership_across_orgs(patch):
    patch("repos", {"org1": [repo("org1", "repo1")], "org2": [repo("org2", "repo2")]})
    patch(
        "team_repos",
        {
            "org1": {"team-rex": ["repo1"], "team-rap": [], "tech-shared": []},
            "org2": {"team-rex": [], "team-rap": ["repo2"], "tech-shared": []},
        },
    )
    assert repos.get_repo_ownership(None, ["org1", "org2"]) == [
        {"organisation": "org1", "repo": "repo1", "owner": "team-rex"},
        {"organisation": "org2", "repo": "repo2", "owner": "team-rap"},
    ]


def test_ignores_ownership_of_archived_repos(patch):
    patch("repos", [repo("the_org", "the_repo", archived_on=date.min)])
    patch(
        "team_repos",
        {"the_org": {"team-rex": ["the_repo"], "team-rap": [], "tech-shared": []}},
    )
    assert repos.get_repo_ownership(None, ["the_org"]) == []


def test_returns_none_for_unknown_ownership(patch):
    patch("repos", [repo("the_org", "the_repo")])
    patch(
        "team_repos", {"the_org": {"team-rex": [], "team-rap": [], "tech-shared": []}}
    )
    assert repos.get_repo_ownership(None, ["the_org"]) == [
        {"organisation": "the_org", "repo": "the_repo", "owner": None}
    ]


def repo(org, name, archived_on=None):
    return Repo(
        org=org,
        name=name,
        created_on=date.min,
        archived_on=archived_on,
        has_vulnerability_alerts_enabled=False,
    )
