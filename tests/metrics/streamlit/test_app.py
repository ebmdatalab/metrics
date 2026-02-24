from collections import defaultdict
from datetime import date, datetime, timedelta

import pytest

import metrics.streamlit.app as app


def test_build_weekly_windows_non_overlapping():
    start = date(2024, 1, 1)
    end = date(2024, 1, 22)

    windows = app.build_weekly_windows(start, end)

    assert [(w.start, w.end) for w in windows] == [
        (date(2024, 1, 1), date(2024, 1, 22)),
    ]


class DummyPR:
    def __init__(self, created_at):
        self.created_at = created_at
        self.merged_at = None

    def was_merged(self):
        return False

    def age_at_end_of(self, date_value):
        next_day = date_value + timedelta(days=1)
        return (
            datetime.combine(next_day, datetime.min.time()) - self.created_at
        ) / timedelta(days=1)


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

    expected = app.working_days_between(
        created, datetime.combine(censor_date + timedelta(days=1), datetime.min.time())
    )
    assert called["durations"] == [expected]


def test_window_count_datapoints_average():
    day = date(2024, 1, 1)
    window = app.Window(day - timedelta(days=7), day)

    prs_by_day = {
        day: [DummyPR(datetime(2024, 1, 1, 0, 0, 0)) for _ in range(2)],
        day - timedelta(days=1): [DummyPR(datetime(2023, 12, 31, 0, 0, 0))],
    }

    data = app.window_count_datapoints(prs_by_day, [window])

    assert data == [app.datapoint(window.end, count=3 / 7)]


def test_window_count_datapoints_average_for_open_counts():
    day = date(2024, 1, 1)
    window = app.Window(day - timedelta(days=7), day)

    prs_by_day = {
        day: [DummyPR(datetime(2024, 1, 1, 0, 0, 0))],
        day - timedelta(days=1): [DummyPR(datetime(2023, 12, 31, 0, 0, 0))],
    }

    data = app.window_count_datapoints(prs_by_day, [window])

    assert data == [app.datapoint(window.end, count=2 / 7)]


def test_xmr_chart_from_series_requires_two_points():
    with pytest.raises(AssertionError):
        app.xmr_chart_from_series(
            [app.datapoint(date(2024, 1, 1), value=0.5)],
            value_field="value",
            y_label="Closed within 2 days",
        )


def test_xmr_chart_from_series_disables_y_axis_label_flush():
    chart = app.xmr_chart_from_series(
        [
            app.datapoint(date(2024, 1, 1), value=1.0),
            app.datapoint(date(2024, 1, 8), value=2.0),
        ],
        value_field="value",
        y_label="Closed within 2 days",
    )
    spec = chart.to_dict()

    assert spec["layer"][0]["encoding"]["y"]["axis"].get("labelFlush") is False


def test_categorise_prs_uses_supplied_today():
    class OpenPR:
        def __init__(self, created_at):
            self.created_at = created_at

        def was_closed(self):
            return False

    created = datetime(2024, 1, 1, 12, 0, 0)
    pr = OpenPR(created)
    supplied_today = date(2024, 1, 3)

    prs_open_by_day, _ = app.categorise_prs([pr], today=supplied_today)

    assert created.date() in prs_open_by_day
    assert date(2024, 1, 2) in prs_open_by_day


def test_closed_within_days_datapoints(monkeypatch):
    day = date(2024, 1, 1)
    window = app.Window(day - timedelta(days=7), day)

    prs_by_day = defaultdict(list)
    prs_by_day[day].append(DummyPR(datetime(2024, 1, 1, 0, 0, 0)))

    def fake_km(flags, durations):
        return [0, 3], [1.0, 0.5]

    monkeypatch.setattr(app.sksurv.nonparametric, "kaplan_meier_estimator", fake_km)

    data = app.closed_within_days_datapoints(prs_by_day, [window], days=3)

    assert data == [app.datapoint(window.end, value=0.5)]


def test_closed_within_days_chart_title(monkeypatch):
    data = [
        app.datapoint(date(2024, 1, 1), value=0.1),
        app.datapoint(date(2024, 1, 8), value=0.2),
    ]

    monkeypatch.setattr(
        app, "closed_within_days_datapoints", lambda *args, **kwargs: data
    )
    chart = app.closed_within_days_chart({}, [], days=4)
    spec = chart.to_dict()

    assert spec["layer"][0]["encoding"]["y"]["title"] is None


def test_working_days_between_excludes_weekends():
    start = datetime(2024, 1, 5, 12, 0, 0)  # Friday noon
    end = datetime(2024, 1, 8, 12, 0, 0)  # Monday noon

    assert app.working_days_between(start, end) == 1.0


def test_build_survival_curve_uses_working_days(monkeypatch):
    created = datetime(2024, 1, 5, 12, 0, 0)
    merged = datetime(2024, 1, 8, 12, 0, 0)

    class PRStub(DummyPR):
        def was_merged(self):
            return True

    pr = PRStub(created)
    pr.merged_at = merged
    day = created.date()
    window = app.Window(day - timedelta(days=1), day)

    called = {}

    def fake_km(flags, durations):
        called["durations"] = durations
        return [0, 1], [1.0, 1.0]

    monkeypatch.setattr(app.sksurv.nonparametric, "kaplan_meier_estimator", fake_km)

    app.build_survival_curve_with_censor_date({day: [pr]}, window, day)

    assert called["durations"] == [1.0]
