import os

import structlog
from sqlalchemy import create_engine, inspect, schema, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import make_url

from ..tools.iter import batched


log = structlog.get_logger()


def delete_rows(connection, name, n=10000):
    """
    Delete N rows from the given table
    """
    sql = text(
        f"""
        DELETE FROM {name}
        WHERE time IN (
            SELECT time
            FROM {name}
            ORDER BY time
            LIMIT :limit
        )
        """
    )
    connection.execute(sql, {"limit": n})


def drop_child_tables(connection, name, n=100):
    sql = text(
        f"""
        SELECT
          child.relname AS child
        FROM
          pg_inherits
          JOIN pg_class AS child ON (inhrelid = child.oid)
          JOIN pg_class AS parent ON (inhparent = parent.oid)
        WHERE
          parent.relname = '{name}'
        """,
    )
    tables = connection.scalars(sql)

    for batch in batched(tables, 100):
        tables = ", ".join(batch)
        connection.execute(text(f"DROP TABLE IF EXISTS {tables}"))


def drop_table(connection, name):
    connection.execute(text(f"DROP TABLE {name}"), {"table_name": name})


def drop_hypertable(engine, table):
    """
    Drop the given table

    We have limited shared memory in our hosted database, so we can't DROP or
    TRUNCATE our hypertables.  Instead for each "raw" table we need to:
     * empty the raw rows (from the named table) in batches
     * drop the sharded "child" tables in batches
     * drop the now empty raw table
    """
    # we don't actually use the Table directly in any of the functions below,
    # so we grab the name here to avoid calling .name everywhere
    table = table.name

    with engine.begin() as connection:
        log.debug("Removing table: %s", table)

        if not has_table(connection, table):
            return

        while has_rows(connection, table):
            delete_rows(connection, table)

        log.debug("Removed all raw rows", table=table)

        drop_child_tables(connection, table)
        log.debug("Removed all child tables", table=table)

        drop_table(connection, table)
        log.debug("Removed raw table", table=table)


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
    return inspect(engine).has_table(table)


def has_rows(connection, name):
    """Count the number of rows in the given table"""
    sql = text(f"SELECT COUNT(*) FROM {name}")
    return connection.scalar(sql) > 0


def reset_table(table, engine=None):
    """Reset the given Table"""
    if engine is None:
        engine = get_engine()

    drop_hypertable(engine, table)
    ensure_table(engine, table)
    log.info("Reset table", table=table.name)


def write(table, rows, engine=None):
    if engine is None:
        engine = get_engine()

    # get the primary key name from the given table
    constraint = inspect(engine).get_pk_constraint(table.name)["name"]

    with engine.begin() as connection:
        # batch our values (which are currently 5 item dicts) so we don't
        # hit the 65535 params limit
        for values in batched(rows, 10_000):
            stmt = insert(table).values(values)

            # use the constraint for this table to drive upserting where the
            # new value (excluded.value) is used to update the row
            do_update_stmt = stmt.on_conflict_do_update(
                constraint=constraint,
                set_={"value": stmt.excluded.value},
            )

            connection.execute(do_update_stmt)
            log.info("Inserted %s rows", len(values), table=table.name)
