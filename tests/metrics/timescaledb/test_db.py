from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import TIMESTAMP, Column, Integer, Table, select, text

from metrics import timescaledb
from metrics.timescaledb.db import ensure_table, get_url, has_rows, has_table
from metrics.timescaledb.tables import metadata


def get_rows(engine, table):
    with engine.connect() as connection:
        return connection.execute(select(table)).all()


def is_hypertable(engine, table):
    sql = """
    SELECT
      count(*)
    FROM
      information_schema.triggers
    WHERE
      event_object_table = :table_name
      AND
      trigger_name = 'ts_insert_blocker';
    """

    with engine.connect() as connection:
        result = connection.execute(text(sql), {"table_name": table.name}).fetchone()

    # We should have one trigger called ts_insert_blocker for a hypertable.
    assert result[0] == 1, result


@pytest.fixture(scope="module")
def table():
    """Dummy table with a time PK because we're testing with timescaledb"""
    return Table(
        "test_table_is_created",
        metadata,
        Column("time", TIMESTAMP(timezone=True), primary_key=True),
        Column("value", Integer),
    )


def test_ensure_table(engine, table):
    with engine.begin() as connection:
        assert not has_table(connection, timescaledb.GitHubPullRequests.name)

    ensure_table(engine, timescaledb.GitHubPullRequests)

    with engine.begin() as connection:
        assert has_table(connection, timescaledb.GitHubPullRequests.name)

    # check there are timescaledb child tables
    # https://stackoverflow.com/questions/1461722/how-to-find-child-tables-that-inherit-from-another-table-in-psql
    is_hypertable(engine, timescaledb.GitHubPullRequests)


def test_get_url(monkeypatch):
    monkeypatch.setenv("TIMESCALEDB_URL", "postgresql://test/db")

    url = get_url()

    assert url.drivername == "postgresql+psycopg"
    assert url.database == "db"


def test_get_url_with_prefix(monkeypatch):
    monkeypatch.setenv("TIMESCALEDB_URL", "postgres://test/db")

    url = get_url(database_prefix="myprefix")

    assert url.database == "myprefix_db"


def test_reset_table(engine):
    ensure_table(engine, timescaledb.GitHubPullRequests)

    # put enough rows in the db to make sure we exercise the batch removal of
    # rows.  timescaledb's write() will ensure the table exists for us.
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

    timescaledb.write(timescaledb.GitHubPullRequests, rows, engine=engine)

    with engine.begin() as connection:
        assert has_table(connection, timescaledb.GitHubPullRequests.name)
        assert has_rows(connection, timescaledb.GitHubPullRequests.name)

    timescaledb.reset_table(timescaledb.GitHubPullRequests, engine=engine)

    with engine.begin() as connection:
        assert has_table(connection, timescaledb.GitHubPullRequests.name)
        assert not has_rows(connection, timescaledb.GitHubPullRequests.name)


def test_write(engine, table):
    # set up a table to write to
    ensure_table(engine, table)

    rows = [
        {"time": datetime(2023, 11, i, tzinfo=UTC), "value": i} for i in range(1, 4)
    ]
    timescaledb.write(table, rows, engine=engine)

    # check rows are in table
    rows = get_rows(engine, table)
    assert len(rows) == 3


def test_write_with_default_engine(table):
    with patch(
        "metrics.timescaledb.db.get_engine", autospec=True
    ) as mocked_create_engine:
        timescaledb.write(table, [])

        mocked_create_engine.assert_called_once()
