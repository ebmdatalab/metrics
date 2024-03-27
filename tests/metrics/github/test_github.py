import datetime

import pytest

from metrics.github import github
from metrics.github.github import PR, Repo


TODAY = datetime.date(year=2023, month=6, day=10)
YESTERDAY = datetime.date(year=2023, month=6, day=9)
TOMORROW = datetime.date(year=2023, month=6, day=11)

LONG_AGO = datetime.date.min

SIX_DAYS = datetime.timedelta(days=6)
ONE_WEEK = datetime.timedelta(weeks=1)


@pytest.fixture
def patch(monkeypatch):
    def patch(query_func, result):
        assert isinstance(result, dict)

        def fake(*keys):
            r = result
            for key in keys:
                r = r[key]
            return r

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
        {
            "opensafely-core": [
                repo_data("ehrql"),
                repo_data("cohort-extractor"),
                repo_data("job-server"),
                repo_data(".github"),
            ],
            "ebmdatalab": [],
        },
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
        {"ebmdatalab": [repo_data("other-repo")], "opensafely-core": []},
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
        {
            "opensafely-core": [repo_data("other-repo", is_archived=True)],
            "ebmdatalab": [],
        },
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
    patch(
        "repos",
        {
            "opensafely-core": [],
            "ebmdatalab": [repo_data("the_repo", is_archived=True)],
        },
    )
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


def test_is_old():
    # A PR is old if it was created a week or more ago.
    assert pr(created_on=LONG_AGO).was_old_on(TODAY)
    assert pr(created_on=TODAY - ONE_WEEK).was_old_on(TODAY)
    assert not pr(created_on=TODAY - SIX_DAYS).was_old_on(TODAY)
    assert not pr(created_on=TODAY).was_old_on(TODAY)

    # PRs that have not yet opened are not old. (This is a real case because we
    # calculate metrics for historic dates.)
    assert not pr(created_on=TODAY + ONE_WEEK).was_old_on(TODAY)

    # Closed PRs are not considered old, as long as they were closed on or before
    # the date that we're interested in.
    assert not pr(created_on=LONG_AGO, closed_on=TODAY - ONE_WEEK).was_old_on(TODAY)
    assert not pr(created_on=LONG_AGO, closed_on=TODAY).was_old_on(TODAY)
    assert pr(created_on=LONG_AGO, closed_on=TODAY + ONE_WEEK).was_old_on(TODAY)


def test_was_merged_in_on():
    assert not pr(merged_on=None).was_merged_on(TODAY)
    assert not pr(merged_on=YESTERDAY).was_merged_on(TODAY)
    assert pr(merged_on=TODAY).was_merged_on(TODAY)
    assert not pr(merged_on=TOMORROW).was_merged_on(TODAY)


def repo_data(name, is_archived=False):
    return dict(
        name=name,
        createdAt=datetime.datetime.min.isoformat(),
        archivedAt=datetime.datetime.now().isoformat() if is_archived else None,
        hasVulnerabilityAlertsEnabled=False,
    )


def repo(org, name, team):
    return Repo(org, name, team, datetime.date.min)


def pr(created_on=TODAY, closed_on=None, merged_on=None):
    return PR(repo("org", "repo", "team"), "author", created_on, merged_on, closed_on)
