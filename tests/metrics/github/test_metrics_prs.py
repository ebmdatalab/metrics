import datetime

import pytest

from metrics.github.github import PR, Repo
from metrics.github.metrics import calculate_pr_counts


TODAY = datetime.date(year=2023, month=6, day=10)
YESTERDAY = datetime.date(year=2023, month=6, day=9)
TWO_DAYS_AGO = datetime.date(year=2023, month=6, day=8)

pytestmark = pytest.mark.freeze_time(TODAY)


def test_makes_counts_for_every_day_between_pr_creation_and_now():
    prs = [pr(repo("an-org", "a-repo"), author="an-author", created_on=TWO_DAYS_AGO)]

    counts = calculate_pr_counts(prs, true)
    assert counts == {
        ("an-org", "a-repo", "an-author", False, TWO_DAYS_AGO): 1,
        ("an-org", "a-repo", "an-author", False, YESTERDAY): 1,
        ("an-org", "a-repo", "an-author", False, TODAY): 1,
    }


def test_counts_prs():
    r = repo("an-org", "a-repo")
    prs = [
        pr(r, author="an-author"),
        pr(r, author="an-author"),
        pr(r, author="an-author"),
    ]

    counts = calculate_pr_counts(prs, true)
    assert counts == {("an-org", "a-repo", "an-author", False, TODAY): 3}


def test_counts_only_prs_matching_predicate():
    r = repo("an-org", "a-repo")
    prs = [
        pr(r, author="an-author", merged_on=TODAY),
        pr(r, author="an-author", merged_on=None),
    ]

    counts = calculate_pr_counts(prs, lambda pr_, _date: pr_.merged_at)
    assert counts == {("an-org", "a-repo", "an-author", False, TODAY): 1}


def test_returns_counts_by_org():
    prs = [
        pr(repo("an-org", "a-repo"), author="an-author"),
        pr(repo("another-org", "another-repo"), author="an-author"),
    ]

    counts = calculate_pr_counts(prs, true)
    assert counts == {
        ("an-org", "a-repo", "an-author", False, TODAY): 1,
        ("another-org", "another-repo", "an-author", False, TODAY): 1,
    }


def test_returns_counts_by_repo():
    prs = [
        pr(repo("an-org", "a-repo"), author="an-author"),
        pr(repo("an-org", "another-repo"), author="an-author"),
    ]

    counts = calculate_pr_counts(prs, true)
    assert counts == {
        ("an-org", "a-repo", "an-author", False, TODAY): 1,
        ("an-org", "another-repo", "an-author", False, TODAY): 1,
    }


def test_returns_counts_by_author():
    r = repo("an-org", "a-repo")
    prs = [pr(r, author="an-author"), pr(r, author="another-author")]

    counts = calculate_pr_counts(prs, true)
    assert counts == {
        ("an-org", "a-repo", "an-author", False, TODAY): 1,
        ("an-org", "a-repo", "another-author", False, TODAY): 1,
    }


def test_distinguishes_content_from_non_content():
    r = repo("an-org", "a-repo")
    prs = [
        pr(r, author="an-author", is_content=True),
        pr(r, author="an-author", is_content=False),
    ]

    counts = calculate_pr_counts(prs, true)
    assert counts == {
        ("an-org", "a-repo", "an-author", False, TODAY): 1,
        ("an-org", "a-repo", "an-author", True, TODAY): 1,
    }


def repo(org, name, is_archived=False):
    return Repo(
        org,
        name,
        "a-team",
        created_on=datetime.date.min,
        is_archived=is_archived,
        has_vulnerability_alerts_enabled=False,
    )


def pr(
    repo_=None,
    created_on=TODAY,
    closed_on=None,
    merged_on=None,
    author=None,
    is_content=False,
):
    return PR(
        repo_,
        author,
        datetime.datetime.combine(created_on, datetime.time()),
        merged_on,
        closed_on,
        is_content,
    )


def true(*_args):
    return True
