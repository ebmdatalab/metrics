from datetime import UTC, datetime

import pytest
from sqlalchemy import TIMESTAMP, Column, Integer, Table, select, text
from sqlalchemy.engine import make_url

from metrics.timescaledb.tables import metadata
from metrics.timescaledb.writer import TIMESCALEDB_URL, TimescaleDBWriter


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


def test_timescaledbwriter(engine, has_table, table):
    # check ensure_table is setting up the table
    assert not has_table(table.name)

    rows = [
        {"time": datetime(2023, 11, i, tzinfo=UTC), "value": i} for i in range(1, 4)
    ]
    with TimescaleDBWriter(table, engine) as db:
        db.write(rows)

    assert has_table(table.name)

    # check there are timescaledb child tables
    # https://stackoverflow.com/questions/1461722/how-to-find-child-tables-that-inherit-from-another-table-in-psql
    is_hypertable(engine, table)

    # check rows are in table
    rows = get_rows(engine, table)
    assert len(rows) == 3


def test_timescaledbwriter_with_default_engine(table):
    db = TimescaleDBWriter(table)
    assert db.engine.url == make_url(TIMESCALEDB_URL), db.engine.url
