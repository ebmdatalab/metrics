from datetime import date, datetime, timedelta


DELTA = timedelta(days=1)


def date_from_iso(value):
    if value is None:
        return date.today()

    return datetime_from_iso(value).date()


def datetime_from_iso(value):
    if value is None:
        return datetime.now()

    return datetime.fromisoformat(value)


def iter_days(start, end, step=DELTA):
    while start <= end:
        yield start
        start += step
