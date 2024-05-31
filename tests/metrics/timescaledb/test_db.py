import datetime

import pytest
from sqlalchemy import TIMESTAMP, Column, Table, Text, create_engine, select, text
from sqlalchemy_utils import create_database, database_exists, drop_database

from metrics.timescaledb import db, tables


@pytest.fixture(scope="module")
def module_scoped_engine():
    url = db._get_url(database_prefix="test")

    # drop the database if it already exists so we start with a clean slate.
    if database_exists(url):  # pragma: no cover
        drop_database(url)

    create_database(url)

    yield create_engine(url)

    # drop the database on test suite exit
    drop_database(url)


@pytest.fixture
def engine(module_scoped_engine, monkeypatch):
    monkeypatch.setattr(db, "_get_engine", lambda: module_scoped_engine)
    yield module_scoped_engine


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
        tables.metadata,
        Column("value", Text, primary_key=True),
    )


@pytest.fixture
def hypertable(request):
    return Table(
        f"{request.function.__name__}_hypertable",
        tables.metadata,
        Column("time", TIMESTAMP(timezone=True), primary_key=True),
        Column("value", Text, primary_key=True),
    )


def test_ensure_table(engine, table):
    with engine.begin() as connection:
        assert not db._has_table(connection, table)

    db._ensure_table(table)

    with engine.begin() as connection:
        assert db._has_table(connection, table)


def test_ensure_hypertable(engine, hypertable):
    with engine.begin() as connection:
        assert not db._has_table(connection, hypertable)

    db._ensure_table(hypertable)

    with engine.begin() as connection:
        assert db._has_table(connection, hypertable)

    # check there are timescaledb child tables
    # https://stackoverflow.com/questions/1461722/how-to-find-child-tables-that-inherit-from-another-table-in-psql
    assert_is_hypertable(engine, hypertable)


def test_get_url(monkeypatch):
    monkeypatch.setenv("TIMESCALEDB_URL", "postgresql://test/db")

    url = db._get_url()

    assert url.drivername == "postgresql+psycopg"
    assert url.database == "db"


def test_get_url_with_prefix(monkeypatch):
    monkeypatch.setenv("TIMESCALEDB_URL", "postgres://test/db")

    url = db._get_url(database_prefix="myprefix")

    assert url.database == "myprefix_db"


def test_reset_table(engine, table):
    db._ensure_table(table)

    # put enough rows in the db to make sure we exercise the batch removal of rows
    batch_size = 5
    rows = []
    for i in range(batch_size * 5):
        rows.append({"value": "reset" + str(i)})

    check_reset(batch_size, engine, rows, table)


def test_reset_hypertable(engine, hypertable):
    db._ensure_table(hypertable)

    # put enough rows in the db to make sure we exercise the batch removal of rows
    batch_size = 5
    rows = []
    start = datetime.date(2020, 4, 1)
    for i in range(batch_size * 5):
        rows.append(
            {"time": start + datetime.timedelta(days=i), "value": "reset" + str(i)}
        )

    check_reset(batch_size, engine, rows, hypertable)


def check_reset(batch_size, engine, rows, table):
    db.write(table, rows)

    with engine.begin() as connection:
        assert db._has_table(connection, table)
        assert db._has_rows(connection, table)

    db.reset_table(table, batch_size=batch_size)

    with engine.begin() as connection:
        assert db._has_table(connection, table)
        assert not db._has_rows(connection, table)


def test_write(engine, table):
    # set up a table to write to
    db._ensure_table(table)

    rows = [{"value": "write" + str(i)} for i in range(1, 4)]
    db.write(table, rows)

    # check rows are in table
    rows = get_rows(engine, table)
    assert len(rows) == 3


def test_upsert(engine, table):
    # add a non-PK column to the table
    table.append_column(Column("value2", Text))

    # insert initial rows
    rows = [{"value": i, "value2": "a"} for i in range(1, 4)]
    db.upsert(table, rows)

    # second batch of rows, some with preexisting value1, some new
    # all with different value2
    rows = [{"value": i, "value2": "b"} for i in range(3, 6)]
    db.upsert(table, rows)

    # check all rows are in table
    rows = get_rows(engine, table)
    assert len(rows) == 5

    # check upsert leaves unmatched rows 1-2 intact
    original_rows = [r for r in rows if int(r[0]) < 3]
    assert original_rows == [("1", "a"), ("2", "a")]

    # check upsert modifies matched row 3 and new rows 4-5
    modified_rows = [r for r in rows if int(r[0]) >= 3]
    assert modified_rows == [("3", "b"), ("4", "b"), ("5", "b")]
