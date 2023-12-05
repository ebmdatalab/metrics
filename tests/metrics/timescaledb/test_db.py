from datetime import date, timedelta

from metrics.timescaledb.db import drop_tables
from metrics.timescaledb.tables import GitHubPullRequests
from metrics.timescaledb.writer import timescaledb_writer


def test_drop_tables(engine, has_table):
    # put enough rows in the db to make sure we exercise the batch removal of
    # rows.  timescaledb_writer() will ensure the table exists for us.
    rows = []
    start = date(2020, 4, 1)
    for i in range(11_000):
        d = start + timedelta(days=i)
        rows.append(
            {
                "time": d,
                "value": i,
                "name": "test",
                "author": "test",
                "repo": "test",
            }
        )

    timescaledb_writer(GitHubPullRequests, rows, engine)

    with engine.begin() as connection:
        drop_tables(connection, prefix="github_")

    assert not has_table(GitHubPullRequests.name)
