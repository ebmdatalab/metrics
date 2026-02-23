from datetime import date, datetime, timedelta

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


class DummyPR:
    def __init__(self, created_at):
        self.created_at = created_at

    def was_merged(self):
        return False

    def age_at_end_of(self, date_value):
        next_day = date_value + timedelta(days=1)
        return (datetime.combine(next_day, datetime.min.time()) - self.created_at) / timedelta(days=1)


def test_build_survival_curve_uses_censor_date(monkeypatch):
    created = datetime(2024, 1, 1, 0, 0, 0)
    pr = DummyPR(created)
    day = created.date()
    window = app.Window(day - timedelta(days=1), day)
    censor_date = date(2024, 1, 3)

    called = {}

    def fake_km(flags, durations):
        called["durations"] = durations
        return [0, 1], [1.0, 1.0]

    monkeypatch.setattr(app.sksurv.nonparametric, "kaplan_meier_estimator", fake_km)

    app.build_survival_curve_with_censor_date({day: [pr]}, window, censor_date)

    assert called["durations"] == [pr.age_at_end_of(censor_date)]
