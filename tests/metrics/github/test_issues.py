from datetime import date

import pytest

from metrics.github.issues import calculate_counts
from metrics.github.query import Issue, Repo


TODAY = date(year=2023, month=6, day=10)
YESTERDAY = date(year=2023, month=6, day=9)
TOMORROW = date(year=2023, month=6, day=11)
TWO_DAYS_AGO = date(year=2023, month=6, day=8)

pytestmark = pytest.mark.freeze_time(TODAY)

REPO = Repo("the-org", "the-repo", created_on=date.min)
AUTHOR = "author"


def test_counts_issue_on_every_day_between_create_and_close():
    issues = {issue(created_on=TWO_DAYS_AGO, closed_on=YESTERDAY)}

    assert calculate_counts(issues) == {
        (REPO.org, REPO.name, AUTHOR, TWO_DAYS_AGO): 1,
        (REPO.org, REPO.name, AUTHOR, YESTERDAY): 1,
    }


def test_counts_issue_on_every_day_up_to_now_if_still_open():
    issues = {issue(created_on=TWO_DAYS_AGO)}

    assert calculate_counts(issues) == {
        (REPO.org, REPO.name, AUTHOR, TWO_DAYS_AGO): 1,
        (REPO.org, REPO.name, AUTHOR, YESTERDAY): 1,
        (REPO.org, REPO.name, AUTHOR, TODAY): 1,
    }


def test_counts_multiple_issues():
    issues = {
        issue(created_on=TWO_DAYS_AGO),
        issue(created_on=YESTERDAY),
        issue(created_on=TODAY),
    }

    assert calculate_counts(issues) == {
        (REPO.org, REPO.name, AUTHOR, TWO_DAYS_AGO): 1,
        (REPO.org, REPO.name, AUTHOR, YESTERDAY): 2,
        (REPO.org, REPO.name, AUTHOR, TODAY): 3,
    }


def test_accounts_for_mixed_closure():
    issues = {
        issue(created_on=TWO_DAYS_AGO, closed_on=YESTERDAY),
        issue(created_on=YESTERDAY),
    }

    assert calculate_counts(issues) == {
        (REPO.org, REPO.name, AUTHOR, TWO_DAYS_AGO): 1,
        (REPO.org, REPO.name, AUTHOR, YESTERDAY): 2,
        (REPO.org, REPO.name, AUTHOR, TODAY): 1,
    }


def test_returns_counts_by_org():
    issues = {
        issue(created_on=TODAY, repo_=repo("org1", "repo")),
        issue(created_on=TODAY, repo_=repo("org2", "repo")),
    }

    assert calculate_counts(issues) == {
        ("org1", "repo", AUTHOR, TODAY): 1,
        ("org2", "repo", AUTHOR, TODAY): 1,
    }


def test_returns_counts_by_repo():
    issues = {
        issue(created_on=TODAY, repo_=repo("org", "repo1")),
        issue(created_on=TODAY, repo_=repo("org", "repo2")),
    }

    assert calculate_counts(issues) == {
        ("org", "repo1", AUTHOR, TODAY): 1,
        ("org", "repo2", AUTHOR, TODAY): 1,
    }


def test_returns_counts_by_author():
    issues = {
        issue(created_on=TODAY, author="author1"),
        issue(created_on=TODAY, author="author2"),
    }

    assert calculate_counts(issues) == {
        (REPO.org, REPO.name, "author1", TODAY): 1,
        (REPO.org, REPO.name, "author2", TODAY): 1,
    }


def repo(org, name, is_archived=False):
    return Repo(
        org,
        name,
        created_on=date.min,
        is_archived=is_archived,
        has_vulnerability_alerts_enabled=False,
    )


def issue(created_on=TODAY, closed_on=None, author=AUTHOR, repo_=REPO):
    return Issue(repo=repo_, author=author, created_on=created_on, closed_on=closed_on)
