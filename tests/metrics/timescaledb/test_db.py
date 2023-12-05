from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import TIMESTAMP, Column, Integer, Table, select, text

from metrics import timescaledb
from metrics.timescaledb.db import TIMESCALEDB_URL, drop_tables
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


def test_drop_tables(engine, has_table):
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

    timescaledb.write(timescaledb.GitHubPullRequests, rows, engine)

    with engine.begin() as connection:
        drop_tables(connection, prefix="github_")

    assert not has_table(timescaledb.GitHubPullRequests.name)


def test_write(engine, has_table, table):
    # check ensure_table is setting up the table
    assert not has_table(table.name)

    rows = [
        {"time": datetime(2023, 11, i, tzinfo=UTC), "value": i} for i in range(1, 4)
    ]
    timescaledb.write(table, rows, engine)

    assert has_table(table.name)

    # check there are timescaledb child tables
    # https://stackoverflow.com/questions/1461722/how-to-find-child-tables-that-inherit-from-another-table-in-psql
    is_hypertable(engine, table)

    # check rows are in table
    rows = get_rows(engine, table)
    assert len(rows) == 3


def test_write_with_default_engine(table):
    with patch(
        "metrics.timescaledb.db.create_engine", autospec=True
    ) as mocked_create_engine:
        timescaledb.write(table, [])

        mocked_create_engine.assert_called_once_with(TIMESCALEDB_URL)
