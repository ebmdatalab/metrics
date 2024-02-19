from datetime import datetime, timedelta


def date_from_iso(value):
    if value is None:
        return None

    return datetime.fromisoformat(value).date()


def iter_days(start, end):
    """
    Days from start to end, inclusive.
    """
    while start <= end:
        yield start
        start += timedelta(days=1)
