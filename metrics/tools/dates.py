from datetime import datetime, timedelta


DELTA = timedelta(days=1)


def date_from_iso(value):
    if value is None:
        return None

    return datetime_from_iso(value).date()


def datetime_from_iso(value):
    if value is None:
        return None

    return datetime.fromisoformat(value)


def iter_days(start, end, step=DELTA):
    while start <= end:
        yield start
        start += step


def previous_weekday(d, weekday):
    """
    Get the date for a previous week day

    Starting at the given date, walk backwards through days until the given
    weekday is found, returning the date for that weekday.

    For example, when giving the date 2023-11-16 and asking for the previous
    Sunday, the returned date would be 2023-11-12.
    """
    output = d

    while output.weekday() != weekday:
        output -= timedelta(days=1)

    return output


def date_before(date_string, target_date):
    if not date_string:
        return False

    return date_from_iso(date_string) <= target_date
