from datetime import date

from metrics.github.prs import process_prs


def test_process_prs():
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
