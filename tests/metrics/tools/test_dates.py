from datetime import date

import pytest

from metrics.tools.dates import (
    date_from_iso,
    iter_days,
    next_weekday,
)


# TODO: remove when we switch to 3.12, this has been added to the calendar
# module in stdlib
MONDAY = 0
TUESDAY = 1
WEDNESDAY = 2
THURSDAY = 3
FRIDAY = 4
SATURDAY = 5
SUNDAY = 6


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, None),
        ("2020-07-08", date(2020, 7, 8)),
        ("2020-07-08T09:12", date(2020, 7, 8)),
    ],
)
def test_date_from_iso(value, expected):
    assert date_from_iso(value) == expected


def test_iter_days():
    dates = list(iter_days(date(2020, 7, 8), date(2020, 7, 10)))

    assert dates == [
        date(2020, 7, 8),
        date(2020, 7, 9),
        date(2020, 7, 10),
    ]


def test_iter_days_with_empty_values():
    with pytest.raises(TypeError):
        list(iter_days(None, date(2020, 7, 8)))

    with pytest.raises(TypeError):
        list(iter_days(date(2020, 7, 8), None))

    with pytest.raises(TypeError):
        list(iter_days(date(2020, 7, 8), date(2022, 7, 8), None))


@pytest.mark.parametrize(
    "d,weekday,expected",
    [
        (date(2023, 11, 9), MONDAY, date(2023, 11, 13)),
        (date(2023, 11, 9), TUESDAY, date(2023, 11, 14)),
        (date(2023, 11, 9), WEDNESDAY, date(2023, 11, 15)),
        (date(2023, 11, 9), THURSDAY, date(2023, 11, 9)),
        (date(2023, 11, 9), FRIDAY, date(2023, 11, 10)),
        (date(2023, 11, 9), SATURDAY, date(2023, 11, 11)),
        (date(2023, 11, 9), SUNDAY, date(2023, 11, 12)),
    ],
    ids=["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
)
def test_next_weekday(d, weekday, expected):
    assert next_weekday(d, weekday) == expected
