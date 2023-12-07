from datetime import date, datetime, time

import pytest

from metrics.github.prs import drop_archived_prs, iter_prs


def test_drop_archived_prs():
    pr1 = {
        "repo_archived_at": datetime(2023, 11, 6),
    }
    pr2 = {
        "repo_archived_at": datetime(2023, 11, 7),
    }
    pr3 = {
        "repo_archived_at": datetime(2023, 11, 8),
    }
    pr4 = {
        "repo_archived_at": None,
    }
    prs = [pr1, pr2, pr3, pr4]

    assert drop_archived_prs(prs, date=date(2023, 11, 7)) == [pr3, pr4]


def test_process_prs_success():
    today = date.today()

    data = [
        {"org": "bennett", "repo": "metrics", "author": "george"},
        {"org": "bennett", "repo": "metrics", "author": "george"},
        {"org": "bennett", "repo": "metrics", "author": "lucy"},
        {"org": "bennett", "repo": "metrics", "author": "tom"},
        {"org": "bennett", "repo": "metrics", "author": "tom"},
        {"org": "bennett", "repo": "metrics", "author": "tom"},
    ]

    # sort so we can use a static list below
    prs = list(
        sorted(
            iter_prs(data, today, name="my-metric"),
            key=lambda pr: pr["author"],
        )
    )

    dt = datetime.combine(today, time())
    expected = [
        {
            "time": dt,
            "value": 2,
            "name": "my-metric",
            "author": "george",
            "organisation": "bennett",
            "repo": "metrics",
        },
        {
            "time": dt,
            "value": 1,
            "name": "my-metric",
            "author": "lucy",
            "organisation": "bennett",
            "repo": "metrics",
        },
        {
            "time": dt,
            "value": 3,
            "name": "my-metric",
            "author": "tom",
            "organisation": "bennett",
            "repo": "metrics",
        },
    ]
    assert prs == expected


def test_process_prs_with_different_orgs():
    data = [
        {"org": "ebmdatalab", "repo": "metrics", "author": "george"},
        {"org": "bennett", "repo": "metrics", "author": "george"},
    ]

    msg = "^Expected 1 org, but found 2 orgs, unsure how to proceed$"
    with pytest.raises(ValueError, match=msg):
        list(iter_prs(data, None, None))
