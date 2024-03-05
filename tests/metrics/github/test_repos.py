from datetime import date

import pytest

from metrics.github import repos
from metrics.github.query import Repo


@pytest.fixture
def patch_query_to_return(monkeypatch):
    def patch(the_repos):
        monkeypatch.setattr(repos.query, "repos", lambda *_args: the_repos)

    return patch


def test_includes_tech_owned_repos(patch_query_to_return):
    patch_query_to_return(
        [repo("ebmdatalab", "sysadmin"), repo("opensafely-core", "job-server")]
    )
    assert len(repos.tech_repos(None, None)) == 2


def test_excludes_non_tech_owned_repos(patch_query_to_return):
    patch_query_to_return(
        [
            repo("ebmdatalab", "clinicaltrials-act-tracker"),
            repo("opensafely-core", "matching"),
        ]
    )
    assert len(repos.tech_repos(None, None)) == 0


def test_dont_exclude_repos_from_unknown_orgs(patch_query_to_return):
    patch_query_to_return([repo("other", "any")])
    assert len(repos.tech_repos(None, None)) == 1


def repo(org, name):
    return Repo(
        org=org,
        name=name,
        created_on=date.min,
        archived_on=None,
        has_vulnerability_alerts_enabled=False,
    )
