import datetime

import pytest

from metrics.tools.dates import (
    date_from_iso,
    iter_days,
)


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, None),
        ("2020-07-08", datetime.date(2020, 7, 8)),
        ("2020-07-08T09:12", datetime.date(2020, 7, 8)),
    ],
)
def test_date_from_iso(value, expected):
    assert date_from_iso(value) == expected


def test_iter_days():
    dates = list(iter_days(datetime.date(2020, 7, 8), datetime.date(2020, 7, 10)))

    assert dates == [
        datetime.date(2020, 7, 8),
        datetime.date(2020, 7, 9),
        datetime.date(2020, 7, 10),
    ]
