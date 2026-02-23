from datetime import date, datetime, timedelta

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


def test_window_counts_skip_small_windows():
    day = date(2024, 1, 1)
    window = app.Window(day - timedelta(days=7), day)

    prs_by_day = {
        day: [DummyPR(datetime(2024, 1, 1, 0, 0, 0)) for _ in range(4)],
    }

    data = app.window_count_datapoints(prs_by_day, [window], min_prs=5)

    assert data == []


def test_window_open_end_of_day_datapoints_average():
    day = date(2024, 1, 1)
    window = app.Window(day - timedelta(days=7), day)

    prs_by_day = {
        day: [DummyPR(datetime(2024, 1, 1, 0, 0, 0)) for _ in range(4)],
    }

    data = app.window_open_end_of_day_datapoints(prs_by_day, [window], min_prs=5)

    assert data == []


def test_two_day_censored_skips_small_windows(monkeypatch):
    day = date(2024, 1, 1)
    window = app.Window(day - timedelta(days=7), day)

    prs_by_day = {
        day: [DummyPR(datetime(2024, 1, 1, 0, 0, 0)) for _ in range(4)],
    }

    def fake_km(flags, durations):
        return [0, 1], [1.0, 1.0]

    monkeypatch.setattr(app.sksurv.nonparametric, "kaplan_meier_estimator", fake_km)

    data = app.two_day_datapoints_censored(prs_by_day, [window], min_prs=5)

    assert data == []


def test_count_chart_weekly_returns_empty_for_small_windows(monkeypatch):
    day = date(2024, 1, 1)
    window = app.Window(day - timedelta(days=7), day)

    prs_by_day = {
        day: [DummyPR(datetime(2024, 1, 1, 0, 0, 0)) for _ in range(4)],
    }

    def fake_xmr(*args, **kwargs):
        raise AssertionError("xmr_chart_from_series should not be called")

    monkeypatch.setattr(app, "xmr_chart_from_series", fake_xmr)
    monkeypatch.setattr(app, "empty_chart", lambda: "empty")

    chart = app.count_chart_weekly(
        "Opened per day (weekly buckets)",
        prs_by_day,
        [window],
        min_prs=5,
    )

    assert chart == "empty"


def test_two_day_chart_weekly_returns_empty_for_small_windows(monkeypatch):
    def fake_xmr(*args, **kwargs):
        raise AssertionError("xmr_chart_from_series should not be called")

    monkeypatch.setattr(app, "two_day_datapoints_censored", lambda *args, **kwargs: [])
    monkeypatch.setattr(app, "xmr_chart_from_series", fake_xmr)
    monkeypatch.setattr(app, "empty_chart", lambda: "empty")

    chart = app.two_day_chart_weekly({}, [])

    assert chart == "empty"


def test_open_end_of_day_chart_weekly_returns_empty_for_small_windows(monkeypatch):
    def fake_xmr(*args, **kwargs):
        raise AssertionError("xmr_chart_from_series should not be called")

    monkeypatch.setattr(
        app,
        "window_open_end_of_day_datapoints",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(app, "xmr_chart_from_series", fake_xmr)
    monkeypatch.setattr(app, "empty_chart", lambda: "empty")

    chart = app.open_end_of_day_chart_weekly({}, [])

    assert chart == "empty"


def test_weekly_bucket_totals_and_histogram_bins():
    day = date(2024, 1, 1)
    windows = [
        app.Window(day - timedelta(days=7), day),
        app.Window(day - timedelta(days=14), day - timedelta(days=7)),
    ]

    prs_by_day = {
        day: [DummyPR(datetime(2024, 1, 1, 0, 0, 0)) for _ in range(3)],
        day - timedelta(days=7): [DummyPR(datetime(2023, 12, 25, 0, 0, 0))],
    }

    totals = app.weekly_bucket_totals(prs_by_day, windows)
    assert totals == [3, 1]

    bins = app.histogram_bins(totals)
    assert bins == {1: 1, 3: 1}


def test_histogram_chart_uses_integer_bins(monkeypatch):
    monkeypatch.setattr(app, "weekly_bucket_totals", lambda *args, **kwargs: [1, 1, 2])
    chart = app.weekly_bucket_histogram_chart({}, [])
    spec = chart.to_dict()

    assert spec["mark"]["type"] == "bar"
    assert spec["encoding"]["x"]["title"] == "PRs opened per bucket"
    assert spec["encoding"]["y"]["title"] == "Number of buckets"
    assert spec["encoding"]["x"]["type"] == "ordinal"


def test_two_day_chart_weekly_title(monkeypatch):
    data = [
        app.datapoint(date(2024, 1, 1), value=0.1),
        app.datapoint(date(2024, 1, 8), value=0.2),
    ]

    monkeypatch.setattr(app, "two_day_datapoints_censored", lambda *args, **kwargs: data)
    chart = app.two_day_chart_weekly({}, [])
    spec = chart.to_dict()

    assert spec["layer"][0]["encoding"]["y"]["title"] == "Closed within 2 days"
