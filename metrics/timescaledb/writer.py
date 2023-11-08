import os
from datetime import datetime, time

import psycopg
import structlog

from . import tables


log = structlog.get_logger()

TIMESCALEDB_URL = os.environ["TIMESCALEDB_URL"]


def ensure_table(name):
    """
    Ensure both the table and hypertable config exist in the database
    """
    run(getattr(tables, name))

    run(
        "SELECT create_hypertable(%s, 'time', if_not_exists => TRUE);",
        [name],
    )

    # ensure the RO grafana user can read the table
    run(f"GRANT SELECT ON {name} TO grafanareader")


def run(sql, *args):
    with psycopg.connect(TIMESCALEDB_URL) as conn:
        cursor = conn.cursor()

        return cursor.execute(sql, *args)


class TimescaleDBWriter:
    def __init__(self, table, key):
        self.key = key
        self.table = table

    def __enter__(self):
        ensure_table(self.table)

        return self

    def __exit__(self, *args):
        pass

    def write(self, date, value, **kwargs):
        # convert date to a timestamp
        # TODO: do we need to do any checking to make sure this is tz-aware and in
        # UTC?
        dt = datetime.combine(date, time())

        # insert into the table set at instantiation
        # unique by the tables `{name}_must_be_different` and we always want to
        # bump the value if that triggers a conflict
        # the columns could differ per table… do we want an object to represent tables?
        if kwargs:
            extra_fields = ", " + ", ".join(kwargs.keys())
            placeholders = ", " + ", ".join(["%s" for k in kwargs.keys()])
        else:
            extra_fields = ""
            placeholders = ""
        sql = f"""
        INSERT INTO {self.table} (time, name, value {extra_fields})
        VALUES (%s, %s, %s {placeholders})
        ON CONFLICT ON CONSTRAINT {self.table}_must_be_different DO UPDATE SET value = EXCLUDED.value;
        """

        run(sql, (dt, self.key, value, *kwargs.values()))

        log.debug(
            self.key,
            date=dt.isoformat(),
            value=value,
            **kwargs,
        )
