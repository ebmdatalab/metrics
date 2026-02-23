from datetime import date

import metrics.streamlit.app as app


def test_build_weekly_windows_non_overlapping():
    start = date(2024, 1, 1)
    end = date(2024, 1, 22)

    windows = app.build_weekly_windows(start, end)

    assert [(w.start, w.end) for w in windows] == [
        (date(2024, 1, 1), date(2024, 1, 8)),
        (date(2024, 1, 8), date(2024, 1, 15)),
        (date(2024, 1, 15), date(2024, 1, 22)),
    ]
