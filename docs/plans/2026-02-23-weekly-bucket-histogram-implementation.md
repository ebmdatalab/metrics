# Weekly Bucket Histogram Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a histogram (integer bins) of PRs opened per weekly bucket at the bottom of the Streamlit dashboard.

**Architecture:** Compute weekly windows, total PRs opened per window (no minimum cutoff), aggregate counts into integer bins, and render a bar chart below existing weekly charts.

**Tech Stack:** Python, Streamlit, Altair, pytest, just.

---

### Task 1: Add weekly bucket totals helper and histogram binning

**Files:**
- Modify: `metrics/streamlit/app.py`
- Test: `tests/metrics/streamlit/test_app.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `just test tests/metrics/streamlit/test_app.py::test_weekly_bucket_totals_and_histogram_bins -v`
Expected: FAIL with `AttributeError` for missing helpers.

**Step 3: Write minimal implementation**

```python
def weekly_bucket_totals(prs_by_day, windows):
    totals = []
    for window in windows:
        totals.append(sum(len(prs_by_day.get(day, [])) for day in window.days()))
    return totals


def histogram_bins(values):
    counts = defaultdict(int)
    for value in values:
        counts[int(value)] += 1
    return dict(sorted(counts.items()))
```

**Step 4: Run test to verify it passes**

Run: `just test tests/metrics/streamlit/test_app.py::test_weekly_bucket_totals_and_histogram_bins -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add metrics/streamlit/app.py tests/metrics/streamlit/test_app.py

git commit -m "Add weekly bucket totals and histogram binning"
```

---

### Task 2: Add histogram chart and wire into display

**Files:**
- Modify: `metrics/streamlit/app.py`
- Test: `tests/metrics/streamlit/test_app.py`

**Step 1: Write the failing test**

```python
def test_histogram_chart_uses_integer_bins(monkeypatch):
    monkeypatch.setattr(app, "weekly_bucket_totals", lambda *args, **kwargs: [1, 1, 2])
    chart = app.weekly_bucket_histogram_chart({}, [])
    spec = chart.to_dict()

    assert spec["mark"]["type"] == "bar"
    assert spec["encoding"]["x"]["title"] == "PRs opened per bucket"
    assert spec["encoding"]["y"]["title"] == "Number of buckets"
```

**Step 2: Run test to verify it fails**

Run: `just test tests/metrics/streamlit/test_app.py::test_histogram_chart_uses_integer_bins -v`
Expected: FAIL with `AttributeError` for missing chart.

**Step 3: Write minimal implementation**

```python
def weekly_bucket_histogram_chart(prs_by_day, windows):
    totals = weekly_bucket_totals(prs_by_day, windows)
    bins = histogram_bins(totals)
    data = [
        {"count": count, "frequency": frequency}
        for count, frequency in bins.items()
    ]

    return (
        altair.Chart(altair.Data(values=data), width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT)
        .mark_bar()
        .encode(
            x=altair.X("count:Q", title="PRs opened per bucket", bin=False),
            y=altair.Y("frequency:Q", title="Number of buckets"),
        )
    )
```

**Step 4: Run test to verify it passes**

Run: `just test tests/metrics/streamlit/test_app.py::test_histogram_chart_uses_integer_bins -v`
Expected: PASS.

**Step 5: Wire into display**

Add `weekly_bucket_histogram_chart(prs_opened_by_day, weekly_windows)` as the last chart in `write_charts(...)`.

**Step 6: Run test to verify it passes**

Run: `just test tests/metrics/streamlit/test_app.py -v`
Expected: PASS.

**Step 7: Commit**

```bash
git add metrics/streamlit/app.py tests/metrics/streamlit/test_app.py

git commit -m "Add weekly bucket histogram chart"
```

---

### Task 3: Full test run

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

