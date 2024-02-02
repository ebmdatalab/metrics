from datetime import date, timedelta

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
        repo("an-org", "a-repo", created_on=TODAY - TWO_WEEKS): [
            {"author": "an-author"},
        ]
    }

    counts = calculate_counts(prs, true)
    assert counts == {
        ("an-org", "a-repo", "an-author", LAST_MONDAY - ONE_WEEK): 1,
        ("an-org", "a-repo", "an-author", LAST_MONDAY): 1,
    }


def test_drops_repos_after_archiving():
    repo_ = repo(
        "an-org",
        "a-repo",
        created_on=TODAY - TWO_WEEKS,
        archived_on=TODAY - ONE_WEEK,
    )
    prs = {
        repo_: [
            {"author": "an-author"},
        ]
    }

    counts = calculate_counts(prs, true)
    assert counts == {
        ("an-org", "a-repo", "an-author", LAST_MONDAY - ONE_WEEK): 1,
    }


def test_includes_archive_date_itself():
    prs = {
        repo("an-org", "a-repo", archived_on=LAST_MONDAY): [
            {"author": "an-author"},
        ]
    }

    counts = calculate_counts(prs, true)
    assert counts == {
        ("an-org", "a-repo", "an-author", LAST_MONDAY): 1,
    }


def test_counts_prs():
    prs = {
        repo("an-org", "a-repo"): [
            {"author": "an-author"},
            {"author": "an-author"},
            {"author": "an-author"},
        ]
    }

    counts = calculate_counts(prs, true)
    assert counts == {("an-org", "a-repo", "an-author", LAST_MONDAY): 3}


def test_counts_only_prs_matching_predicate():
    prs = {
        repo("an-org", "a-repo"): [
            {"author": "an-author", "merged_on": TODAY},
            {"author": "an-author", "merged_on": None},
        ]
    }

    counts = calculate_counts(prs, lambda pr, _date: pr["merged_on"] == TODAY)
    assert counts == {("an-org", "a-repo", "an-author", LAST_MONDAY): 1}


def test_returns_counts_by_org():
    prs = {
        repo("an-org", "a-repo"): [{"author": "an-author"}],
        repo("another-org", "another-repo"): [{"author": "an-author"}],
    }

    counts = calculate_counts(prs, true)
    assert counts == {
        ("an-org", "a-repo", "an-author", LAST_MONDAY): 1,
        ("another-org", "another-repo", "an-author", LAST_MONDAY): 1,
    }


def test_returns_counts_by_repo():
    prs = {
        repo("an-org", "a-repo"): [{"author": "an-author"}],
        repo("an-org", "another-repo"): [{"author": "an-author"}],
    }

    counts = calculate_counts(prs, true)
    assert counts == {
        ("an-org", "a-repo", "an-author", LAST_MONDAY): 1,
        ("an-org", "another-repo", "an-author", LAST_MONDAY): 1,
    }


def test_returns_counts_by_author():
    prs = {
        repo("an-org", "a-repo"): [
            {"author": "an-author"},
            {"author": "another-author"},
        ]
    }

    counts = calculate_counts(prs, true)
    assert counts == {
        ("an-org", "a-repo", "an-author", LAST_MONDAY): 1,
        ("an-org", "a-repo", "another-author", LAST_MONDAY): 1,
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


def test_was_merged_in_week_ending():
    # Unmerged PR is unmerged
    assert not was_merged_in_week_ending(pr(merged_on=None), TODAY)

    assert not was_merged_in_week_ending(pr(merged_on=LONG_AGO), TODAY)
    assert not was_merged_in_week_ending(pr(merged_on=TODAY - ONE_WEEK), TODAY)
    assert was_merged_in_week_ending(pr(merged_on=TODAY - SIX_DAYS), TODAY)
    assert was_merged_in_week_ending(pr(merged_on=TODAY), TODAY)
    assert not was_merged_in_week_ending(pr(merged_on=TODAY + ONE_DAY), TODAY)
    assert not was_merged_in_week_ending(pr(merged_on=DISTANT_FUTURE), TODAY)


def repo(org, name, created_on=RECENTLY, archived_on=None):
    return FrozenDict(
        {
            "org": org,
            "name": name,
            "created_on": created_on,
            "archived_on": archived_on if archived_on else None,
        }
    )


def pr(created_on=None, closed_on=None, merged_on=None):
    return {
        "created_on": created_on if created_on else None,
        "closed_on": closed_on if closed_on else None,
        "merged_on": merged_on if merged_on else None,
    }


def true(*_args):
    return True
