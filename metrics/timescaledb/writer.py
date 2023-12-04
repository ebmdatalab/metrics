import os

import structlog
from sqlalchemy import create_engine, inspect, schema, text
from sqlalchemy.dialects.postgresql import insert

from ..tools.iter import batched


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
    def __init__(self, table, engine=None):
        if engine is None:
            engine = create_engine(TIMESCALEDB_URL)

        self.engine = engine
        self.table = table

    def __enter__(self):
        ensure_table(self.engine, self.table)

        return self

    def __exit__(self, *args, **kwargs):
        pass

    def write(self, rows):
        # get the primary key name from the given table
        constraint = inspect(self.engine).get_pk_constraint(self.table.name)["name"]

        with self.engine.begin() as connection:
            # batch our values (which are currently 5 item dicts) so we don't
            # hit the 65535 params limit
            for values in batched(rows, 10_000):
                stmt = insert(self.table).values(values)

                # use the constraint for this table to drive upserting where the
                # new value (excluded.value) is used to update the row
                do_update_stmt = stmt.on_conflict_do_update(
                    constraint=constraint,
                    set_={"value": stmt.excluded.value},
                )

                connection.execute(do_update_stmt)
                log.info("Inserted %s rows", len(values), table=self.table.name)
