# Working-Day Duration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Use working-time duration (exclude weekend time) for the "Closed within 2 days" metric, remove the 1–5 day charts, remove histogram, and drop empty-bucket handling.

**Architecture:** Replace closed-within-2-days duration calculation with a helper that counts only weekday time between timestamps. Use that helper for both merged and censored observations. Keep weekly buckets (3-week) and only a single closed-within-2-days chart.

**Tech Stack:** Python, Streamlit, Altair, pytest, just.

---

### Task 1: Implement working-time duration helper

**Files:**
- Modify: `metrics/streamlit/app.py`
- Test: `tests/metrics/streamlit/test_app.py`

**Step 1: Write the failing test**

```python
def test_working_days_between_excludes_weekends():
    start = datetime(2024, 1, 5, 12, 0, 0)  # Friday noon
    end = datetime(2024, 1, 8, 12, 0, 0)    # Monday noon

    # 24h of working time: Fri noon -> Fri midnight (12h) + Mon midnight -> Mon noon (12h)
    assert app.working_days_between(start, end) == 1.0
```

**Step 2: Run test to verify it fails**

Run: `just test tests/metrics/streamlit/test_app.py::test_working_days_between_excludes_weekends -v`
Expected: FAIL with `AttributeError` for missing helper.

**Step 3: Write minimal implementation**

```python
def working_days_between(start, end):
    if end <= start:
        return 0.0

    total_seconds = 0.0
    current = start
    while current.date() <= end.date():
        day_start = datetime.datetime.combine(current.date(), datetime.time(0, 0, 0, tzinfo=current.tzinfo))
        day_end = day_start + datetime.timedelta(days=1)

        segment_start = max(current, day_start)
        segment_end = min(end, day_end)

        if segment_start < segment_end and segment_start.weekday() < 5:
            total_seconds += (segment_end - segment_start).total_seconds()

        current = day_end

    return total_seconds / datetime.timedelta(days=1).total_seconds()
```

**Step 4: Run test to verify it passes**

Run: `just test tests/metrics/streamlit/test_app.py::test_working_days_between_excludes_weekends -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add metrics/streamlit/app.py tests/metrics/streamlit/test_app.py

git commit -m "Add working-day duration helper"
```

---

### Task 2: Apply working-time duration to survival curve inputs

**Files:**
- Modify: `metrics/streamlit/app.py`
- Test: `tests/metrics/streamlit/test_app.py`

**Step 1: Write the failing test**

```python
def test_build_survival_curve_uses_working_days(monkeypatch):
    created = datetime(2024, 1, 5, 12, 0, 0)
    merged = datetime(2024, 1, 8, 12, 0, 0)

    class PRStub(DummyPR):
        def was_merged(self):
            return True

        def age_when_merged(self):
            return (merged - created) / timedelta(days=1)

    pr = PRStub(created)
    day = created.date()
    window = app.Window(day - timedelta(days=1), day)

    called = {}

    def fake_km(flags, durations):
        called["durations"] = durations
        return [0, 1], [1.0, 1.0]

    monkeypatch.setattr(app.sksurv.nonparametric, "kaplan_meier_estimator", fake_km)

    app.build_survival_curve_with_censor_date({day: [pr]}, window, day)

    assert called["durations"] == [1.0]
```

**Step 2: Run test to verify it fails**

Run: `just test tests/metrics/streamlit/test_app.py::test_build_survival_curve_uses_working_days -v`
Expected: FAIL until working-time duration is used.

**Step 3: Write minimal implementation**

```python
# In build_survival_curve_with_censor_date:
# - replace pr.age_when_merged() with working_days_between(pr.created_at, pr.merged_at)
# - replace pr.age_at_end_of(censor_date) with working_days_between(pr.created_at, end_datetime)
#   where end_datetime is end of censor_date
```

**Step 4: Run test to verify it passes**

Run: `just test tests/metrics/streamlit/test_app.py::test_build_survival_curve_uses_working_days -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add metrics/streamlit/app.py tests/metrics/streamlit/test_app.py

git commit -m "Use working-day duration in survival curve"
```

---

### Task 3: Remove histogram and extra closed-within charts

**Files:**
- Modify: `metrics/streamlit/app.py`
- Test: `tests/metrics/streamlit/test_app.py`

**Step 1: Write the failing test**

```python
# No direct unit test; rely on existing tests and smoke checks.
```

**Step 2: Run test to verify it fails**

Run: `just test tests/metrics/streamlit/test_app.py -v`
Expected: PASS unless wiring errors are introduced.

**Step 3: Write minimal implementation**

```python
# In display(): remove closed_within_days_chart for days 1,3,4,5 and keep only days=2.
# Remove weekly_bucket_histogram_chart call.
# Remove histogram helper functions and related tests.
# Remove empty-bucket handling (min_prs and empty_chart) already removed in code.
```

**Step 4: Run test to verify it passes**

Run: `just test tests/metrics/streamlit/test_app.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add metrics/streamlit/app.py tests/metrics/streamlit/test_app.py

git commit -m "Simplify charts and remove histogram"
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

