from datetime import date, datetime

import pytest

from metrics.github.prs import drop_archived_prs, process_prs


def test_drop_archived_prs():
    pr1 = {
        "repo_archived": date(2023, 11, 6),
        "repo_archived_at": datetime(2023, 11, 6),
    }
    pr2 = {
        "repo_archived": date(2023, 11, 7),
        "repo_archived_at": datetime(2023, 11, 7),
    }
    pr3 = {
        "repo_archived": date(2023, 11, 8),
        "repo_archived_at": datetime(2023, 11, 8),
    }
    pr4 = {
        "repo_archived": None,
        "repo_archived_at": None,
    }
    prs = [pr1, pr2, pr3, pr4]

    assert drop_archived_prs(prs, date=date(2023, 11, 7)) == [pr3, pr4]
    assert drop_archived_prs(prs, date=datetime(2023, 11, 7)) == [pr3, pr4]


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

    output = []

    class Writer:
        def write(self, date, count, *, name, author, organisation, repo):
            output.append(
                {
                    "author": author,
                    "count": count,
                    "date": date,
                    "name": name,
                    "organisation": organisation,
                    "repo": repo,
                }
            )

    process_prs(Writer(), data, today, name="my-metric")

    george = [pr for pr in output if pr["author"] == "george"][0]
    assert george["count"] == 2

    lucy = [pr for pr in output if pr["author"] == "lucy"][0]
    assert lucy["count"] == 1

    tom = [pr for pr in output if pr["author"] == "tom"][0]
    assert tom["count"] == 3


def test_process_prs_with_different_orgs():
    data = [
        {"org": "ebmdatalab", "repo": "metrics", "author": "george"},
        {"org": "bennett", "repo": "metrics", "author": "george"},
    ]

    msg = "^Expected 1 org, but found 2 orgs, unsure how to proceed$"
    with pytest.raises(ValueError, match=msg):
        process_prs(None, data, None)
