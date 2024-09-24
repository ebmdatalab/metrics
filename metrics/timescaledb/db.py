import functools
import os

import structlog
from sqlalchemy import create_engine, inspect, schema, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import make_url

from ..tools.iter import batched


log = structlog.get_logger()


def reset_table(table, batch_size=None):
    with _get_engine().begin() as connection:
        _drop_table(connection, table, batch_size)
        _ensure_table(connection, table)
        log.info("Reset table", table=table.name)


def write(table, rows):
    batch_size = _batch_size(table)

    with _get_engine().begin() as connection:
        for values in batched(rows, batch_size):
            connection.execute(insert(table).values(values))
            log.info("Inserted %s rows", len(values), table=table.name)


def upsert(table, rows):
    _ensure_table(table)
    batch_size = _batch_size(table)
    non_pk_columns = set(table.columns) - set(table.primary_key.columns)

    # use the primary key constraint to match rows to be updated,
    # using default constraint name if not otherwise specified
    constraint = table.primary_key.name or table.name + "_pkey"

    with _get_engine().begin() as connection:
        for values in batched(rows, batch_size):
            # Construct a PostgreSQL "INSERT..ON CONFLICT" style upsert statement
            # https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#insert-on-conflict-upsert

            # "Vanilla" statement to start, we need this to be able to derive
            # the "excluded" columns in the values which we need to use to update
            # the target table in case of conflict on the constraint
            insert_stmt = insert(table).values(values)

            # This dict dicates which columns in the target table are updated (the
            # non-PK columns) and the corresponding values with which they are updated
            update_set_clause = {
                c: insert_stmt.excluded[c.name] for c in non_pk_columns
            }

            # Extend the insert statement to include checking for row conflicts using
            # the primary key constraint and telling the database to update
            # the conflicting rows according to the SET clause
            insert_stmt = insert_stmt.on_conflict_do_update(
                constraint=constraint,
                set_=update_set_clause,
            )
            connection.execute(insert_stmt)
            log.info("Inserted %s rows", len(values), table=table.name)


def _batch_size(table):
    max_params = 65535  # limit for postgresql
    return max_params // len(table.columns)


def _drop_table(connection, table, batch_size, cascade=False):
    log.debug("Removing table: %s", table.name)

    if not _has_table(connection, table):
        return

    if _is_hypertable(table):
        # We have limited shared memory in our hosted database, so we can't DROP or
        # TRUNCATE our hypertables.  Instead for each "raw" table we need to:
        #  * empty the raw rows (from the named table) in batches
        #  * drop the sharded "child" tables in batches
        #  * drop the now empty raw table
        while _has_rows(connection, table):
            _delete_rows(connection, table, batch_size)

        log.debug("Removed all raw rows", table=table.name)

        _drop_child_tables(connection, table)
        log.debug("Removed all child tables", table=table.name)

    connection.execute(text(f"DROP TABLE {table.name}"))

    log.debug("Removed raw table", table=table.name)


def _has_table(connection, table):
    return inspect(connection).has_table(table.name)


def _is_hypertable(table):
    return "time" in table.columns


def _has_rows(connection, table):
    sql = text(f"SELECT COUNT(*) FROM {table.name}")
    return connection.scalar(sql) > 0


def _delete_rows(connection, table, batch_size=10000):
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


def _drop_child_tables(connection, table):
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


def _ensure_table(connection, table):
    connection.execute(schema.CreateTable(table, if_not_exists=True))

    if _is_hypertable(table):
        connection.execute(
            text(
                f"SELECT create_hypertable('{table.name}', 'time', if_not_exists => TRUE);"
            )
        )


@functools.cache
def _get_engine():
    return create_engine(_get_url())


def _get_url(database_prefix=None):
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
