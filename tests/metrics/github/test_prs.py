from datetime import date, datetime, time, timedelta

import pytest

from metrics.github.prs import calculate_counts, is_old, was_merged_in_week_ending
from metrics.github.query import FrozenDict


TODAY = date(year=2023, month=12, day=1)  # a Friday
LAST_MONDAY = date(year=2023, month=11, day=27)  # a Monday
RECENTLY = date(year=2023, month=11, day=24)  # just a few days before the Monday

LONG_AGO = date.min
DISTANT_FUTURE = date.max

ONE_DAY = timedelta(days=1)
SIX_DAYS = timedelta(days=6)
ONE_WEEK = timedelta(weeks=1)
TWO_WEEKS = timedelta(weeks=2)

pytestmark = pytest.mark.freeze_time(TODAY)


def test_makes_counts_for_mondays_between_repo_creation_and_now():
    prs = {
        repo("a-repo", created_at=TODAY - TWO_WEEKS): [
            {"author": "an-author"},
        ]
    }

    counts = calculate_counts(prs, true)
    assert counts == {
        ("a-repo", "an-author", LAST_MONDAY - ONE_WEEK): 1,
        ("a-repo", "an-author", LAST_MONDAY): 1,
    }


def test_drops_repos_after_archiving():
    prs = {
        repo("a-repo", created_at=TODAY - TWO_WEEKS, archived_at=TODAY - ONE_WEEK): [
            {"author": "an-author"},
        ]
    }

    counts = calculate_counts(prs, true)
    assert counts == {
        ("a-repo", "an-author", LAST_MONDAY - ONE_WEEK): 1,
    }


def test_includes_archive_date_itself():
    prs = {
        repo("a-repo", archived_at=LAST_MONDAY): [
            {"author": "an-author"},
        ]
    }

    counts = calculate_counts(prs, true)
    assert counts == {
        ("a-repo", "an-author", LAST_MONDAY): 1,
    }


def test_counts_prs():
    prs = {
        repo("a-repo"): [
            {"author": "an-author"},
            {"author": "an-author"},
            {"author": "an-author"},
        ]
    }

    counts = calculate_counts(prs, true)
    assert counts == {("a-repo", "an-author", LAST_MONDAY): 3}


def test_counts_only_prs_matching_predicate():
    prs = {
        repo("a-repo"): [
            {"author": "an-author", "merged_at": TODAY},
            {"author": "an-author", "merged_at": None},
        ]
    }

    counts = calculate_counts(prs, lambda pr, _date: pr["merged_at"] == TODAY)
    assert counts == {("a-repo", "an-author", LAST_MONDAY): 1}


def test_returns_counts_by_repo():
    prs = {
        repo("a-repo"): [{"author": "an-author"}],
        repo("another-repo"): [{"author": "an-author"}],
    }

    counts = calculate_counts(prs, true)
    assert counts == {
        ("a-repo", "an-author", LAST_MONDAY): 1,
        ("another-repo", "an-author", LAST_MONDAY): 1,
    }


def test_returns_counts_by_author():
    prs = {
        repo("a-repo"): [
            {"author": "an-author"},
            {"author": "another-author"},
        ]
    }

    counts = calculate_counts(prs, true)
    assert counts == {
        ("a-repo", "an-author", LAST_MONDAY): 1,
        ("a-repo", "another-author", LAST_MONDAY): 1,
    }


def test_is_old():
    # A PR is old if it was created a week or more ago.
    assert is_old(pr(created_at=LONG_AGO), TODAY)
    assert is_old(pr(created_at=TODAY - ONE_WEEK), TODAY)
    assert not is_old(pr(created_at=TODAY - SIX_DAYS), TODAY)
    assert not is_old(pr(created_at=TODAY), TODAY)

    # PRs that have not yet opened are not old. (This is a real case because we
    # calculate metrics for historic dates.)
    assert not is_old(pr(created_at=TODAY + ONE_WEEK), TODAY)

    # Closed PRs are not considered old, as long as they were closed on or before
    # the date that we're interested in.
    assert not is_old(pr(created_at=LONG_AGO, closed_at=TODAY - ONE_WEEK), TODAY)
    assert not is_old(pr(created_at=LONG_AGO, closed_at=TODAY), TODAY)
    assert is_old(pr(created_at=LONG_AGO, closed_at=TODAY + ONE_WEEK), TODAY)


def test_was_merged_in_week_ending():
    # Unmerged PR is unmerged
    assert not was_merged_in_week_ending(pr(merged_at=None), TODAY)

    assert not was_merged_in_week_ending(pr(merged_at=LONG_AGO), TODAY)
    assert not was_merged_in_week_ending(pr(merged_at=TODAY - ONE_WEEK), TODAY)
    assert was_merged_in_week_ending(pr(merged_at=TODAY - SIX_DAYS), TODAY)
    assert was_merged_in_week_ending(pr(merged_at=TODAY), TODAY)
    assert not was_merged_in_week_ending(pr(merged_at=TODAY + ONE_DAY), TODAY)
    assert not was_merged_in_week_ending(pr(merged_at=DISTANT_FUTURE), TODAY)


def repo(name, created_at=RECENTLY, archived_at=None):
    return FrozenDict(
        {
            "name": name,
            "created_at": datetime.combine(created_at, time()),
            "archived_at": (
                datetime.combine(archived_at, time()) if archived_at else None
            ),
        }
    )


def pr(created_at=None, closed_at=None, merged_at=None):
    return {
        "created_at": datetime.combine(created_at, time()) if created_at else None,
        "closed_at": datetime.combine(closed_at, time()) if closed_at else None,
        "merged_at": datetime.combine(merged_at, time()) if merged_at else None,
    }


def true(*_args):
    return True
