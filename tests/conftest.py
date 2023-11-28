import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url
from sqlalchemy_utils import create_database, database_exists, drop_database

from metrics.timescaledb.writer import TIMESCALEDB_URL


@pytest.fixture(scope="session", autouse=True)
def engine():
    # build a sqlalchemy.URL from the TIMESCALEDB_URL env var but prepend test_
    # to the database name
    url = make_url(TIMESCALEDB_URL)
    url = url.set(database=f"test_{url.database}")

    # drop the database if it already exists so we start with a clean slate.
    if database_exists(url):  # pragma: no cover
        drop_database(url)

    create_database(url)

    yield create_engine(url)

    # drop the database on test suite exit
    drop_database(url)


@pytest.fixture
def has_table(engine):
    def checker(table_name):
        return inspect(engine).has_table(table_name)

    return checker
