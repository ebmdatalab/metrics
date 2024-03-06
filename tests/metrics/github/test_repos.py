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
        "repos", [repo("ebmdatalab", "sysadmin"), repo("opensafely-core", "job-server")]
    )
    assert len(repos.tech_repos(None, None)) == 2


def test_excludes_non_tech_owned_repos(patch):
    patch(
        "repos",
        [
            repo("ebmdatalab", "clinicaltrials-act-tracker"),
            repo("opensafely-core", "matching"),
        ],
    )
    assert len(repos.tech_repos(None, None)) == 0


def test_dont_exclude_repos_from_unknown_orgs(patch):
    patch("repos", [repo("other", "any")])
    assert len(repos.tech_repos(None, None)) == 1


def test_looks_up_ownership(patch):
    patch("repos", [repo("the_org", "repo1"), repo("the_org", "repo2")])
    patch("team_repos", {"the_org": {"team-rex": ["repo1"], "team-rap": ["repo2"]}})
    assert repos.get_repo_ownership(None, ["the_org"]) == [
        {"organisation": "the_org", "repo": "repo1", "owner": "team-rex"},
        {"organisation": "the_org", "repo": "repo2", "owner": "team-rap"},
    ]


def test_looks_up_ownership_across_orgs(patch):
    patch("repos", {"org1": [repo("org1", "repo1")], "org2": [repo("org2", "repo2")]})
    patch(
        "team_repos",
        {
            "org1": {"team-rex": ["repo1"], "team-rap": []},
            "org2": {"team-rex": [], "team-rap": ["repo2"]},
        },
    )
    assert repos.get_repo_ownership(None, ["org1", "org2"]) == [
        {"organisation": "org1", "repo": "repo1", "owner": "team-rex"},
        {"organisation": "org2", "repo": "repo2", "owner": "team-rap"},
    ]


def test_ignores_ownership_of_archived_repos(patch):
    patch("repos", [repo("the_org", "the_repo", archived_on=date.min)])
    patch("team_repos", {"the_org": {"team-rex": ["the_repo"], "team-rap": []}})
    assert repos.get_repo_ownership(None, ["the_org"]) == []


def test_returns_none_for_unknown_ownership(patch):
    patch("repos", [repo("the_org", "the_repo")])
    patch("team_repos", {"the_org": {"team-rex": [], "team-rap": []}})
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
