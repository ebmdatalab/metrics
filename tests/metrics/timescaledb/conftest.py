import pytest
from sqlalchemy import create_engine
from sqlalchemy_utils import create_database, database_exists, drop_database

from metrics.timescaledb.db import get_url


@pytest.fixture(scope="session", autouse=True)
def engine():
    url = get_url(database_prefix="test")

    # drop the database if it already exists so we start with a clean slate.
    if database_exists(url):  # pragma: no cover
        drop_database(url)

    create_database(url)

    yield create_engine(url)

    # drop the database on test suite exit
    drop_database(url)
