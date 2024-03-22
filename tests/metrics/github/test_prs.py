from datetime import date, timedelta

import pytest

from metrics.github.prs import calculate_counts, is_old, was_merged_on
from metrics.github.repos import Repo


TODAY = date(year=2023, month=6, day=10)
YESTERDAY = date(year=2023, month=6, day=9)
TOMORROW = date(year=2023, month=6, day=11)
TWO_DAYS_AGO = date(year=2023, month=6, day=8)

LONG_AGO = date.min

SIX_DAYS = timedelta(days=6)
ONE_WEEK = timedelta(weeks=1)

pytestmark = pytest.mark.freeze_time(TODAY)


def test_makes_counts_for_every_day_between_pr_creation_and_now():
    prs = {
        repo("an-org", "a-repo"): [
            pr(author="an-author", created_on=TWO_DAYS_AGO),
        ]
    }

    counts = calculate_counts(prs, true)
    assert counts == {
        ("an-org", "a-repo", "an-author", TWO_DAYS_AGO): 1,
        ("an-org", "a-repo", "an-author", YESTERDAY): 1,
        ("an-org", "a-repo", "an-author", TODAY): 1,
    }


def test_counts_prs():
    prs = {
        repo("an-org", "a-repo"): [
            pr(author="an-author"),
            pr(author="an-author"),
            pr(author="an-author"),
        ]
    }

    counts = calculate_counts(prs, true)
    assert counts == {("an-org", "a-repo", "an-author", TODAY): 3}


def test_counts_only_prs_matching_predicate():
    prs = {
        repo("an-org", "a-repo"): [
            pr(author="an-author", merged_on=TODAY),
            pr(author="an-author", merged_on=None),
        ]
    }

    counts = calculate_counts(prs, lambda pr, _date: pr["merged_on"])
    assert counts == {("an-org", "a-repo", "an-author", TODAY): 1}


def test_returns_counts_by_org():
    prs = {
        repo("an-org", "a-repo"): [pr(author="an-author")],
        repo("another-org", "another-repo"): [pr(author="an-author")],
    }

    counts = calculate_counts(prs, true)
    assert counts == {
        ("an-org", "a-repo", "an-author", TODAY): 1,
        ("another-org", "another-repo", "an-author", TODAY): 1,
    }


def test_returns_counts_by_repo():
    prs = {
        repo("an-org", "a-repo"): [pr(author="an-author")],
        repo("an-org", "another-repo"): [pr(author="an-author")],
    }

    counts = calculate_counts(prs, true)
    assert counts == {
        ("an-org", "a-repo", "an-author", TODAY): 1,
        ("an-org", "another-repo", "an-author", TODAY): 1,
    }


def test_returns_counts_by_author():
    prs = {
        repo("an-org", "a-repo"): [
            pr(author="an-author"),
            pr(author="another-author"),
        ]
    }

    counts = calculate_counts(prs, true)
    assert counts == {
        ("an-org", "a-repo", "an-author", TODAY): 1,
        ("an-org", "a-repo", "another-author", TODAY): 1,
    }


def test_is_old():
    # A PR is old if it was created a week or more ago.
    assert is_old(pr(created_on=LONG_AGO), TODAY)
    assert is_old(pr(created_on=TODAY - ONE_WEEK), TODAY)
    assert not is_old(pr(created_on=TODAY - SIX_DAYS), TODAY)
    assert not is_old(pr(created_on=TODAY), TODAY)

    # PRs that have not yet opened are not old. (This is a real case because we
    # calculate metrics for historic dates.)
    assert not is_old(pr(created_on=TODAY + ONE_WEEK), TODAY)

    # Closed PRs are not considered old, as long as they were closed on or before
    # the date that we're interested in.
    assert not is_old(pr(created_on=LONG_AGO, closed_on=TODAY - ONE_WEEK), TODAY)
    assert not is_old(pr(created_on=LONG_AGO, closed_on=TODAY), TODAY)
    assert is_old(pr(created_on=LONG_AGO, closed_on=TODAY + ONE_WEEK), TODAY)


def test_was_merged_in_on():
    assert not was_merged_on(pr(merged_on=None), TODAY)
    assert not was_merged_on(pr(merged_on=YESTERDAY), TODAY)
    assert was_merged_on(pr(merged_on=TODAY), TODAY)
    assert not was_merged_on(pr(merged_on=TOMORROW), TODAY)


def repo(org, name, is_archived=False):
    return Repo(
        org,
        name,
        created_on=date.min,
        is_archived=is_archived,
        has_vulnerability_alerts_enabled=False,
    )


def pr(created_on=TODAY, closed_on=None, merged_on=None, author=None):
    return {
        "created_on": created_on,
        "closed_on": closed_on,
        "merged_on": merged_on,
        "author": author,
    }


def true(*_args):
    return True
