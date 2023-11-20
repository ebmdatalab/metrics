from datetime import date

import pytest
from sqlalchemy import TIMESTAMP, Column, Integer, Table, inspect, select, text
from sqlalchemy.engine import make_url

from metrics.timescaledb.tables import metadata
from metrics.timescaledb.writer import TIMESCALEDB_URL, TimescaleDBWriter


def get_rows(engine, table):
    with engine.connect() as connection:
        return connection.execute(select(table)).all()


def has_grant(engine, table):
    sql = """
    SELECT
      privilege_type
    FROM
      information_schema.role_table_grants
    WHERE
      table_name = :table_name
      AND grantee = 'grafanareader';
    """

    with engine.connect() as connection:
        result = connection.execute(text(sql), {"table_name": table.name}).fetchmany()

    assert len(result) == 1

    assert result[0][0] == "SELECT"


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


def test_timescaledbwriter(engine, table):
    # check ensure_table is setting up the table
    assert not inspect(engine).has_table(table.name)

    with TimescaleDBWriter(table, engine) as writer:
        for i in range(1, 4):
            writer.write(date(2023, 11, i), i)

    assert inspect(engine).has_table(table.name)

    # check there are timescaledb child tables
    # https://stackoverflow.com/questions/1461722/how-to-find-child-tables-that-inherit-from-another-table-in-psql
    is_hypertable(engine, table)

    # check grant
    # https://stackoverflow.com/questions/7336413/query-grants-for-a-table-in-postgres
    has_grant(engine, table)

    # check rows are in table
    rows = get_rows(engine, table)
    assert len(rows) == 3


def test_timescaledbwriter_with_default_engine(table):
    writer = TimescaleDBWriter(table)
    assert writer.engine.url == make_url(TIMESCALEDB_URL), writer.engine.url
