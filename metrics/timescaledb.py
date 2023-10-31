from datetime import datetime, time

import psycopg
import structlog


log = structlog.get_logger()

CONNECTION = "postgres://postgres:password@localhost:5433/tsdb"


def run(sql, *args):
    with psycopg.connect(CONNECTION) as conn:
        cursor = conn.cursor()

        return cursor.execute(sql, *args)


def write(key, date, value, tags=None):
    # convert date to a timestamp
    # TODO: do we need to do any checking to make sure this is tz-aware and in
    # UTC?
    dt = datetime.combine(date, time())

    name = key.removeprefix("github_pull_requests_")

    sql = """
    INSERT INTO github_pull_requests (time, name, value, author, organisation, repo)
    VALUES (%s, %s, %s, %s, %s, %s);
    """

    run(sql, (dt, name, value, *tags.values()))

    log.debug(
        name,
        date=dt.isoformat(),
        value=value,
        **tags,
    )
