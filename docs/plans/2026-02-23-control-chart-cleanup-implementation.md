# Weekly Chart Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Simplify the Streamlit dashboard to a consistent set of weekly, non-overlapping control charts and remove obsolete charts.

**Architecture:** Use weekly windows for all remaining control charts. Keep the scatterplot. Replace open-at-end-of-day with a weekly average of daily open counts. Remove sliding-window charts, team breakdown, and stacked probabilities.

**Tech Stack:** Python, Streamlit, Altair, scikit-survival, pytest, just.

---

### Task 1: Add weekly open-at-end-of-day datapoints helper

**Files:**
- Modify: `metrics/streamlit/app.py`
- Test: `tests/metrics/streamlit/test_app.py`

**Step 1: Write the failing test**

```python
def test_window_open_end_of_day_datapoints_average():
    day = date(2024, 1, 1)
    window = app.Window(day - timedelta(days=7), day)

    prs_by_day = {
        day: [DummyPR(datetime(2024, 1, 1, 0, 0, 0)) for _ in range(4)],
    }

    data = app.window_open_end_of_day_datapoints(prs_by_day, [window], min_prs=5)

    assert data == []
```

**Step 2: Run test to verify it fails**

Run: `just test tests/metrics/streamlit/test_app.py::test_window_open_end_of_day_datapoints_average -v`
Expected: FAIL with `AttributeError` for missing helper.

**Step 3: Write minimal implementation**

```python
def window_open_end_of_day_datapoints(prs, windows, min_prs=None):
    count_data = []

    for window in windows:
        window_counts = [len(prs.get(day, [])) for day in window.days()]
        window_total = sum(window_counts)
        if min_prs is not None and window_total < min_prs:
            continue
        count_data.append(datapoint(window.end, count=statistics.mean(window_counts)))

    return count_data
```

**Step 4: Run test to verify it passes**

Run: `just test tests/metrics/streamlit/test_app.py::test_window_open_end_of_day_datapoints_average -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add metrics/streamlit/app.py tests/metrics/streamlit/test_app.py

git commit -m "Add weekly open-at-end-of-day datapoints helper"
```

---

### Task 2: Add weekly open-at-end-of-day chart

**Files:**
- Modify: `metrics/streamlit/app.py`
- Test: `tests/metrics/streamlit/test_app.py`

**Step 1: Write the failing test**

```python
def test_open_end_of_day_chart_weekly_returns_empty_for_small_windows(monkeypatch):
    def fake_xmr(*args, **kwargs):
        raise AssertionError("xmr_chart_from_series should not be called")

    monkeypatch.setattr(app, "window_open_end_of_day_datapoints", lambda *args, **kwargs: [])
    monkeypatch.setattr(app, "xmr_chart_from_series", fake_xmr)
    monkeypatch.setattr(app, "empty_chart", lambda: "empty")

    chart = app.open_end_of_day_chart_weekly({}, [])

    assert chart == "empty"
```

**Step 2: Run test to verify it fails**

Run: `just test tests/metrics/streamlit/test_app.py::test_open_end_of_day_chart_weekly_returns_empty_for_small_windows -v`
Expected: FAIL with `AttributeError` for missing helper.

**Step 3: Write minimal implementation**

```python
def open_end_of_day_chart_weekly(prs, windows):
    count_data = window_open_end_of_day_datapoints(
        prs, windows, min_prs=MIN_PRS_PER_WINDOW
    )
    if len(count_data) < 2:
        return empty_chart()

    return xmr_chart_from_series(
        count_data,
        value_field="count",
        y_title="Open at end of day",
    )
```

**Step 4: Run test to verify it passes**

Run: `just test tests/metrics/streamlit/test_app.py::test_open_end_of_day_chart_weekly_returns_empty_for_small_windows -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add metrics/streamlit/app.py tests/metrics/streamlit/test_app.py

git commit -m "Add weekly open-at-end-of-day chart"
```

---

### Task 3: Remove obsolete charts and wire final order

**Files:**
- Modify: `metrics/streamlit/app.py`
- Test: `tests/metrics/streamlit/test_app.py`

**Step 1: Write the failing test**

```python
# No direct unit test; use existing tests and smoke checks.
```

**Step 2: Run test to verify it fails**

Run: `just test tests/metrics/streamlit/test_app.py -v`
Expected: PASS unless wiring errors are introduced.

**Step 3: Write minimal implementation**

```python
# In display(), keep:
# - scatter_chart
# - count_chart_weekly (Opened per day)
# - open_end_of_day_chart_weekly
# - two_day_chart_weekly
# Remove:
# - count_chart("Opened per day", ...)
# - count_chart("Open at end of day", ...)
# - two_day_chart (sliding)
# - two_day_chart_censored (sliding)
# - team_two_day_chart
# - probabilities_chart
# Simplify y-axis labels:
# - Opened per day
# - Open at end of day
# - Closed within 2 days
```

**Step 4: Run test to verify it passes**

Run: `just test tests/metrics/streamlit/test_app.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add metrics/streamlit/app.py

git commit -m "Simplify dashboard to weekly charts"
```

---

### Task 4: Full test run

**Files:**
- Test: `tests/metrics/streamlit/test_app.py`

**Step 1: Run full tests**

Run: `just test`
Expected: FAIL in unrelated suites (known pre-existing failures). Record failures.

**Step 2: Commit (if needed)**

```bash
git status --short
```

Expected: clean worktree.

