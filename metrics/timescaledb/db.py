import os

import structlog
from sqlalchemy import create_engine, inspect, schema, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import make_url

from ..tools.iter import batched


log = structlog.get_logger()


def delete_rows(connection, table, batch_size=10000):
    sql = text(
        f"""
        DELETE FROM {table.name}
        WHERE time IN (
            SELECT time
            FROM {table.name}
            ORDER BY time
            LIMIT :limit
        )
        """
    )
    connection.execute(sql, {"limit": batch_size})


def drop_child_tables(connection, table):
    sql = text(
        f"""
        SELECT
          child.relname AS child
        FROM
          pg_inherits
          JOIN pg_class AS child ON (inhrelid = child.oid)
          JOIN pg_class AS parent ON (inhparent = parent.oid)
        WHERE
          parent.relname = '{table.name}'
        """,
    )
    tables = connection.scalars(sql)

    for batch in batched(tables, 100):
        tables = ", ".join(batch)
        connection.execute(text(f"DROP TABLE IF EXISTS {tables}"))


def drop_table(connection, name):
    connection.execute(text(f"DROP TABLE {name}"), {"table_name": name})


def drop_hypertable(engine, table, batch_size):
    """
    Drop the given table

    We have limited shared memory in our hosted database, so we can't DROP or
    TRUNCATE our hypertables.  Instead for each "raw" table we need to:
     * empty the raw rows (from the named table) in batches
     * drop the sharded "child" tables in batches
     * drop the now empty raw table
    """
    with engine.begin() as connection:
        log.debug("Removing table: %s", table.name)

        if not has_table(connection, table):
            return

        while has_rows(connection, table):
            delete_rows(connection, table, batch_size)

        log.debug("Removed all raw rows", table=table.name)

        drop_child_tables(connection, table)
        log.debug("Removed all child tables", table=table.name)

        drop_table(connection, table)
        log.debug("Removed raw table", table=table.name)


def ensure_table(engine, table):
    """
    Ensure both the table and hypertable config exist in the database
    """
    with engine.begin() as connection:
        connection.execute(schema.CreateTable(table, if_not_exists=True))

    with engine.begin() as connection:
        connection.execute(
            text(
                f"SELECT create_hypertable('{table.name}', 'time', if_not_exists => TRUE);"
            )
        )


def get_engine():
    return create_engine(get_url())


def get_url(database_prefix=None):
    """
    Get the final database connection URL

    We split this out from get_engine() so the tests can possibly drop the
    database first, and because we need to set the dialect before we use the
    URL.
    """
    # psycopg2 is still the default postgres dialect for sqlalchemy so we inject
    # +psycopg to enable using v3.
    raw_url = os.environ["TIMESCALEDB_URL"].replace("postgresql", "postgresql+psycopg")

    # build a sqlalchemy.URL from the url and append a prefix if one has been passed in
    url = make_url(raw_url)
    if database_prefix:
        url = url.set(database=f"{database_prefix}_{url.database}")

    return url


def has_table(engine, table):
    return inspect(engine).has_table(table.name)


def has_rows(connection, table):
    sql = text(f"SELECT COUNT(*) FROM {table.name}")
    return connection.scalar(sql) > 0


def reset_table(table, engine=None, batch_size=None):
    if engine is None:
        engine = get_engine()

    drop_hypertable(engine, table, batch_size)
    ensure_table(engine, table)
    log.info("Reset table", table=table.name)


def write(table, rows, engine=None):
    if engine is None:
        engine = get_engine()

    max_params = 65535  # limit for postgresql
    batch_size = max_params // len(table.columns)

    with engine.begin() as connection:
        for values in batched(rows, batch_size):
            connection.execute(insert(table).values(values))
            log.info("Inserted %s rows", len(values), table=table.name)
