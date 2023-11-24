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


class TimescaleDBWriter:
    values = []

    def __init__(self, table, engine=None):
        if engine is None:
            engine = create_engine(TIMESCALEDB_URL)

        self.engine = engine
        self.table = table

    def __enter__(self):
        ensure_table(self.engine, self.table)

        return self

    def __exit__(self, *args):
        # get the primary key name from the given table
        constraint = inspect(self.engine).get_pk_constraint(self.table.name)["name"]

        log.debug("Will insert %s rows", len(self.values), table=self.table.name)
        with self.engine.begin() as connection:
            stmt = insert(self.table).values(self.values)

            # use the constraint for this table to drive upserting where the
            # new value (excluded.value) is used to update the row
            do_update_stmt = stmt.on_conflict_do_update(
                constraint=constraint,
                set_={"value": stmt.excluded.value},
            )

            connection.execute(do_update_stmt)

        log.debug("Inserted %s rows", len(self.values), table=self.table.name)

    def write(self, date, value, **kwargs):
        # convert date to a timestamp
        # TODO: do we need to do any checking to make sure this is tz-aware and in
        # UTC?
        dt = datetime.combine(date, time())
        value = {"time": dt, "value": value, **kwargs}

        self.values.append(value)
