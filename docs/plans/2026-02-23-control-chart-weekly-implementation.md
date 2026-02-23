# Weekly Control Chart Without Smoothing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add weekly non-overlapping control charts (with window-end censoring) for "Closed within 2 days" and "Opened per day", plus a censoring-fixed sliding-window 2-day chart, while keeping the current chart for comparison.

**Architecture:** Introduce weekly window builder, a survival curve helper that accepts a censor date, and shared helpers for per-window datapoints with a minimum PR threshold. Wire new charts into the Streamlit dashboard directly below existing ones.

**Tech Stack:** Python, Streamlit, Altair, scikit-survival, pytest, just.

---

### Task 1: Add window + datapoint helpers

**Files:**
- Modify: `metrics/streamlit/app.py`
- Test: `tests/metrics/streamlit/test_app.py`

**Step 1: Write the failing test**

```python
from datetime import date, datetime, timedelta

import metrics.streamlit.app as app


def test_build_weekly_windows_non_overlapping():
    start = date(2024, 1, 1)
    end = date(2024, 1, 22)

    windows = app.build_weekly_windows(start, end)

    assert [(w.start, w.end) for w in windows] == [
        (date(2024, 1, 15), date(2024, 1, 22)),
        (date(2024, 1, 8), date(2024, 1, 15)),
        (date(2024, 1, 1), date(2024, 1, 8)),
    ]
```

**Step 2: Run test to verify it fails**

Run: `just test -- tests/metrics/streamlit/test_app.py::test_build_weekly_windows_non_overlapping -v`
Expected: FAIL with `AttributeError: module 'metrics.streamlit.app' has no attribute 'build_weekly_windows'`.

**Step 3: Write minimal implementation**

```python
WEEKLY_BUCKET_DAYS = 7
MIN_PRS_PER_WINDOW = 5


def build_weekly_windows(start_date, end_date):
    window_size = datetime.timedelta(days=WEEKLY_BUCKET_DAYS)

    windows = []
    end = end_date
    while (start := end - window_size) >= start_date:
        windows.append(Window(start, end))
        end -= window_size

    return list(reversed(windows))
```

**Step 4: Run test to verify it passes**

Run: `just test -- tests/metrics/streamlit/test_app.py::test_build_weekly_windows_non_overlapping -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add metrics/streamlit/app.py tests/metrics/streamlit/test_app.py

git commit -m "Add weekly window builder"
```

---

### Task 2: Add window-end censoring helper

**Files:**
- Modify: `metrics/streamlit/app.py`
- Test: `tests/metrics/streamlit/test_app.py`

**Step 1: Write the failing test**

```python
from datetime import datetime, date, timedelta

import metrics.streamlit.app as app


class DummyPR:
    def __init__(self, created_at):
        self.created_at = created_at

    def was_merged(self):
        return False

    def age_at_end_of(self, date_value):
        return (datetime.combine(date_value + timedelta(days=1), datetime.min.time()) - self.created_at) / timedelta(days=1)


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
```

**Step 2: Run test to verify it fails**

Run: `just test -- tests/metrics/streamlit/test_app.py::test_build_survival_curve_uses_censor_date -v`
Expected: FAIL with `AttributeError` for missing helper.

**Step 3: Write minimal implementation**

```python

def build_survival_curve_with_censor_date(prs, window, censor_date):
    observation_flags = []
    durations = []

    for day in window.days():
        for pr in prs[day]:
            if pr.was_merged():
                observation_flags.append(True)
                durations.append(pr.age_when_merged())
            else:
                observation_flags.append(False)
                durations.append(pr.age_at_end_of(censor_date))

    times, probs = sksurv.nonparametric.kaplan_meier_estimator(
        observation_flags, durations
    )

    def prob_of_surviving_for_days(days):
        if days == 0:
            return 1.0
        return numpy.interp([days], times, probs)[0]

    return prob_of_surviving_for_days
```

**Step 4: Run test to verify it passes**

Run: `just test -- tests/metrics/streamlit/test_app.py::test_build_survival_curve_uses_censor_date -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add metrics/streamlit/app.py tests/metrics/streamlit/test_app.py

git commit -m "Add survival curve helper with window-end censoring"
```

---

### Task 3: Add per-window datapoint helpers and min PR filtering

**Files:**
- Modify: `metrics/streamlit/app.py`
- Test: `tests/metrics/streamlit/test_app.py`

**Step 1: Write the failing test**

```python
from datetime import date, datetime, timedelta

import metrics.streamlit.app as app


class DummyPR:
    def __init__(self, created_at):
        self.created_at = created_at


def test_window_counts_skip_small_windows():
    day = date(2024, 1, 1)
    window = app.Window(day - timedelta(days=7), day)

    prs_by_day = {day: [DummyPR(datetime(2024, 1, 1, 0, 0, 0)) for _ in range(4)]}

    data = app.window_count_datapoints(prs_by_day, [window], min_prs=5)

    assert data == []
```

**Step 2: Run test to verify it fails**

Run: `just test -- tests/metrics/streamlit/test_app.py::test_window_counts_skip_small_windows -v`
Expected: FAIL with `AttributeError` for missing helper.

**Step 3: Write minimal implementation**

```python

def window_count_datapoints(prs, windows, min_prs=None):
    count_data = []

    for window in windows:
        window_counts = [len(prs[day]) for day in window.days()]
        window_total = sum(window_counts)
        if min_prs is not None and window_total < min_prs:
            continue
        count_data.append(datapoint(window.end, count=statistics.mean(window_counts)))

    return count_data
```

**Step 4: Run test to verify it passes**

Run: `just test -- tests/metrics/streamlit/test_app.py::test_window_counts_skip_small_windows -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add metrics/streamlit/app.py tests/metrics/streamlit/test_app.py

git commit -m "Add window count datapoints helper"
```

---

### Task 4: Add censoring-fixed sliding 2-day chart

**Files:**
- Modify: `metrics/streamlit/app.py`
- Test: `tests/metrics/streamlit/test_app.py`

**Step 1: Write the failing test**

```python
from datetime import date, datetime, timedelta

import metrics.streamlit.app as app


def test_two_day_censored_skips_small_windows(monkeypatch):
    day = date(2024, 1, 1)
    window = app.Window(day - timedelta(days=7), day)

    class DummyPR:
        def __init__(self, created_at):
            self.created_at = created_at

        def was_merged(self):
            return False

        def age_at_end_of(self, date_value):
            return 1

    prs_by_day = {day: [DummyPR(datetime(2024, 1, 1, 0, 0, 0)) for _ in range(4)]}

    def fake_km(flags, durations):
        return [0, 1], [1.0, 1.0]

    monkeypatch.setattr(app.sksurv.nonparametric, "kaplan_meier_estimator", fake_km)

    data = app.two_day_datapoints_censored(prs_by_day, [window], min_prs=5)

    assert data == []
```

**Step 2: Run test to verify it fails**

Run: `just test -- tests/metrics/streamlit/test_app.py::test_two_day_censored_skips_small_windows -v`
Expected: FAIL with `AttributeError` for missing helper.

**Step 3: Write minimal implementation**

```python

def two_day_datapoints_censored(prs, windows, min_prs=None):
    probabilities_data = []
    for window in windows:
        window_total = sum(len(prs[day]) for day in window.days())
        if min_prs is not None and window_total < min_prs:
            continue

        prob_of_survival = build_survival_curve_with_censor_date(
            prs, window, window.end
        )
        prob_closed_within_two_days = 1 - prob_of_survival(2)
        probabilities_data.append(
            datapoint(window.end, value=prob_closed_within_two_days)
        )

    return probabilities_data
```

**Step 4: Run test to verify it passes**

Run: `just test -- tests/metrics/streamlit/test_app.py::test_two_day_censored_skips_small_windows -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add metrics/streamlit/app.py tests/metrics/streamlit/test_app.py

git commit -m "Add censored two-day datapoints helper"
```

---

### Task 5: Wire new charts into Streamlit display

**Files:**
- Modify: `metrics/streamlit/app.py`

**Step 1: Write the failing test**

```python
# No direct unit test; validate via targeted functions + smoke test for imports.
```

**Step 2: Run test to verify it fails**

Run: `just test -- tests/metrics/streamlit/test_app.py -v`
Expected: FAIL until wiring is complete.

**Step 3: Write minimal implementation**

```python
# add in display():
# - weekly_windows = build_weekly_windows(START_DATE, END_DATE - ONE_DAY)
# - add count_chart for weekly opened per day (weekly buckets)
# - add two_day_chart_censored for sliding windows with censoring
# - add two_day_chart_weekly for weekly buckets

# add chart builders:
# def count_chart_weekly(...): uses window_count_datapoints(..., min_prs=MIN_PRS_PER_WINDOW)
# def two_day_chart_censored(...): uses two_day_datapoints_censored(...)
# def two_day_chart_weekly(...): uses two_day_datapoints_censored with weekly windows
```

**Step 4: Run test to verify it passes**

Run: `just test -- tests/metrics/streamlit/test_app.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add metrics/streamlit/app.py

git commit -m "Add weekly and censoring-fixed charts"
```

---

### Task 6: Full test run

**Files:**
- Test: `tests/metrics/streamlit/test_app.py`

**Step 1: Run full tests**

Run: `just test`
Expected: PASS (report any failures before proceeding).

**Step 2: Commit (if needed)**

```bash
git status --short
```

Expected: clean worktree.

