from datetime import UTC, date, datetime, time, timedelta

import pytest

from metrics.github.prs import (
    drop_archived_prs,
    iter_prs,
    old_prs,
    pr_throughput,
)


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


def ts(name, author, time, value):
    return {
        "time": time,
        "value": value,
        "name": name,
        "author": author,
        "repo": "metrics",
        "organisation": "bennett",
    }


def test_old_prs():
    def pr(author, created, days_open):
        created_at = datetime(2023, 11, created, tzinfo=UTC)
        closed_at = created_at + timedelta(days=days_open)

        return {
            "org": "bennett",
            "repo": "metrics",
            "author": author,
            "closed_at": closed_at,
            "created_at": created_at,
            "repo_archived_at": closed_at + timedelta(days=1),
        }

    week1 = [  # 2023-11-06 -> 2023-11-12
        pr("bbc", created=1, days_open=8),
        pr("bbc", created=7, days_open=1),
        pr("bbc", created=10, days_open=1),
        pr("george", created=2, days_open=9),
        pr("george", created=3, days_open=7),
        pr("george", created=9, days_open=1),
        pr("george", created=10, days_open=1),
        pr("george", created=11, days_open=1),
        pr("lucy", created=5, days_open=7),
        pr("tom", created=9, days_open=1),
    ]
    week2 = [  # 2023-11-13 -> 2023-11-19
        pr("bbc", created=15, days_open=3),
        pr("george", created=14, days_open=2),
        pr("george", created=16, days_open=1),
        pr("lucy", created=6, days_open=10),
        pr("lucy", created=11, days_open=8),
        pr("lucy", created=14, days_open=2),
        pr("lucy", created=18, days_open=1),
        pr("tom", created=9, days_open=8),
        pr("tom", created=10, days_open=5),
        pr("tom", created=15, days_open=2),
    ]
    week3 = [  # 2023-11-20 -> 2023-11-26
        pr("bbc", created=15, days_open=9),
        pr("george", created=21, days_open=2),
        pr("lucy", created=16, days_open=10),
        pr("lucy", created=16, days_open=9),
        pr("lucy", created=16, days_open=8),
        pr("lucy", created=16, days_open=7),
        pr("lucy", created=24, days_open=3),
        pr("lucy", created=25, days_open=2),
        pr("lucy", created=25, days_open=3),
        pr("tom", created=18, days_open=8),
    ]
    week4 = [  # 2023-11-27 -> 2023-12-03
        pr("bbc", created=21, days_open=9),
        pr("george", created=21, days_open=10),
        pr("george", created=22, days_open=9),
        pr("george", created=23, days_open=8),
        pr("george", created=24, days_open=7),
        pr("george", created=25, days_open=6),
        pr("george", created=26, days_open=5),
        pr("lucy", created=28, days_open=2),
        pr("lucy", created=30, days_open=1),
        pr("tom", created=24, days_open=9),
    ]
    prs = week1 + week2 + week3 + week4

    outputs = list(old_prs(prs, days_threshold=7))

    def output_for_week(starting_day, outputs):
        # break up the outputs to make them easier to work with when asserting
        dt = datetime(2023, 11, starting_day)
        return list(
            sorted(
                [row for row in outputs if row["time"] == dt],
                key=lambda pr: pr["author"],
            )
        )

    # we expect to only have timeseries (ts) rows people with counts of PRs
    # which have been open past the threshold specified in the old_prs() call

    # week 1
    assert output_for_week(6, outputs) == [
        ts("queue_older_than_7_days", "bbc", datetime(2023, 11, 6), 1),
        ts("queue_older_than_7_days", "george", datetime(2023, 11, 6), 2),
        ts("queue_older_than_7_days", "lucy", datetime(2023, 11, 6), 1),
    ]

    # week 2
    assert output_for_week(13, outputs) == [
        ts("queue_older_than_7_days", "lucy", datetime(2023, 11, 13), 2),
        ts("queue_older_than_7_days", "tom", datetime(2023, 11, 13), 1),
    ]

    # week 3
    assert output_for_week(20, outputs) == [
        ts("queue_older_than_7_days", "bbc", datetime(2023, 11, 20), 1),
        ts("queue_older_than_7_days", "lucy", datetime(2023, 11, 20), 4),
        ts("queue_older_than_7_days", "tom", datetime(2023, 11, 20), 1),
    ]

    # week 4
    assert output_for_week(27, outputs) == [
        ts("queue_older_than_7_days", "bbc", datetime(2023, 11, 27), 1),
        ts("queue_older_than_7_days", "george", datetime(2023, 11, 27), 4),
        ts("queue_older_than_7_days", "tom", datetime(2023, 11, 27), 1),
    ]


def test_pr_throughput():
    def pr(author, merged):
        merged_at = datetime(2023, 11, merged)
        return {
            "org": "bennett",
            "repo": "metrics",
            "author": author,
            "created_at": merged_at - timedelta(days=1),
            "merged_at": merged_at,
            "repo_archived_at": merged_at + timedelta(days=1),
        }

    prs = [
        pr("george", merged=1),
        pr("george", merged=1),
        pr("george", merged=1),
        pr("bbc", merged=1),
        pr("bbc", merged=1),
        pr("george", merged=2),
        pr("bbc", merged=2),
        pr("bbc", merged=2),
        pr("bbc", merged=2),
        pr("bbc", merged=2),
    ]

    # should have rows with expected counts
    expected = [
        ts("prs_merged", "bbc", datetime(2023, 11, 1), 2),
        ts("prs_merged", "george", datetime(2023, 11, 1), 3),
        ts("prs_merged", "bbc", datetime(2023, 11, 2), 4),
        ts("prs_merged", "george", datetime(2023, 11, 2), 1),
    ]

    # the output so we can compare consistently
    output = list(sorted(pr_throughput(prs), key=lambda r: (r["time"], r["author"])))

    assert output == expected
