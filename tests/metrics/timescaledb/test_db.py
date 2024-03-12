from datetime import date, timedelta

import pytest
from sqlalchemy import TIMESTAMP, Column, Table, Text, select, text

from metrics import timescaledb
from metrics.timescaledb.db import ensure_table, get_url, has_rows, has_table
from metrics.timescaledb.tables import metadata


def get_rows(engine, table):
    with engine.connect() as connection:
        return connection.execute(select(table)).all()


def assert_is_hypertable(engine, table):
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


@pytest.fixture
def table(request):
    return Table(
        f"{request.function.__name__}_table",
        metadata,
        Column("value", Text, primary_key=True),
    )


@pytest.fixture
def hypertable(request):
    return Table(
        f"{request.function.__name__}_hypertable",
        metadata,
        Column("time", TIMESTAMP(timezone=True), primary_key=True),
        Column("value", Text, primary_key=True),
    )


def test_ensure_table(engine, table):
    with engine.begin() as connection:
        assert not has_table(connection, table)

    ensure_table(engine, table)

    with engine.begin() as connection:
        assert has_table(connection, table)


def test_ensure_hypertable(engine, hypertable):
    with engine.begin() as connection:
        assert not has_table(connection, hypertable)

    ensure_table(engine, hypertable)

    with engine.begin() as connection:
        assert has_table(connection, hypertable)

    # check there are timescaledb child tables
    # https://stackoverflow.com/questions/1461722/how-to-find-child-tables-that-inherit-from-another-table-in-psql
    assert_is_hypertable(engine, hypertable)


def test_get_url(monkeypatch):
    monkeypatch.setenv("TIMESCALEDB_URL", "postgresql://test/db")

    url = get_url()

    assert url.drivername == "postgresql+psycopg"
    assert url.database == "db"


def test_get_url_with_prefix(monkeypatch):
    monkeypatch.setenv("TIMESCALEDB_URL", "postgres://test/db")

    url = get_url(database_prefix="myprefix")

    assert url.database == "myprefix_db"


def test_reset_table(engine, table):
    ensure_table(engine, table)

    # put enough rows in the db to make sure we exercise the batch removal of rows
    batch_size = 5
    rows = []
    for i in range(batch_size * 5):
        rows.append({"value": "reset" + str(i)})

    check_reset(batch_size, engine, rows, table)


def test_reset_hypertable(engine, hypertable):
    ensure_table(engine, hypertable)

    # put enough rows in the db to make sure we exercise the batch removal of rows
    batch_size = 5
    rows = []
    start = date(2020, 4, 1)
    for i in range(batch_size * 5):
        rows.append({"time": start + timedelta(days=i), "value": "reset" + str(i)})

    check_reset(batch_size, engine, rows, hypertable)


def check_reset(batch_size, engine, rows, table):
    timescaledb.write(table, rows, engine=engine)

    with engine.begin() as connection:
        assert has_table(connection, table)
        assert has_rows(connection, table)

    timescaledb.reset_table(table, engine=engine, batch_size=batch_size)

    with engine.begin() as connection:
        assert has_table(connection, table)
        assert not has_rows(connection, table)


def test_write(engine, table):
    # set up a table to write to
    ensure_table(engine, table)

    rows = [{"value": "write" + str(i)} for i in range(1, 4)]
    timescaledb.write(table, rows, engine=engine)

    # check rows are in table
    rows = get_rows(engine, table)
    assert len(rows) == 3
