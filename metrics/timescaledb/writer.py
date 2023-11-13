import os
from datetime import datetime, time

import structlog
from sqlalchemy import create_engine, inspect, schema, text
from sqlalchemy.dialects.postgresql import insert


log = structlog.get_logger()

# Note: psycopg2 is still the default postgres dialect for sqlalchemy so we
# inject +psycopg to enable using v3
TIMESCALEDB_URL = os.environ["TIMESCALEDB_URL"].replace(
    "postgresql", "postgresql+psycopg"
)
engine = create_engine(TIMESCALEDB_URL)


def ensure_table(table):
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

        # ensure the RO grafana user can read the table
        connection.execute(text(f"GRANT SELECT ON {table.name} TO grafanareader"))


class TimescaleDBWriter:
    inserts = []

    def __init__(self, table):
        self.table = table

    def __enter__(self):
        ensure_table(self.table)

        return self

    def __exit__(self, *args):
        with engine.begin() as connection:
            for stmt in self.inserts:
                connection.execute(stmt)

    def write(self, date, value, **kwargs):
        # convert date to a timestamp
        # TODO: do we need to do any checking to make sure this is tz-aware and in
        # UTC?
        dt = datetime.combine(date, time())

        # get the primary key name from the given table
        constraint = inspect(engine).get_pk_constraint(self.table.name)["name"]

        # TODO: could we put do all the rows at once in the values() call and
        # then use EXCLUDED to reference the value in the set_?
        insert_stmt = (
            insert(self.table)
            .values(time=dt, value=value, **kwargs)
            .on_conflict_do_update(
                constraint=constraint,
                set_={"value": value},
            )
        )

        self.inserts.append(insert_stmt)

        log.debug(insert_stmt)
