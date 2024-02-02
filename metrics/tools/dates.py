from datetime import datetime, timedelta


def date_from_iso(value):
    if value is None:
        return None

    return datetime_from_iso(value).date()


def datetime_from_iso(value):
    if value is None:
        return None

    return datetime.fromisoformat(value)


def iter_days(start, end, step=timedelta(days=1)):
    """
    Days from start to end, inclusive. Single day steps by default.
    """
    while start <= end:
        yield start
        start += step


def next_weekday(date_, weekday):
    """
    Get the date of the next {Mon,Tue,Wed,Thu,Fri,Sat,Sun}day on or following the given date.

    The weekday is an integer, Monday being 0.
    """
    output = date_

    while output.weekday() != weekday:
        output += timedelta(days=1)

    return output
