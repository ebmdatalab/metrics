# Weekly control chart without smoothing (design)

## Goal
Add a new control chart for "Closed within 2 days" that uses non-overlapping weekly buckets and window-end censoring (no sliding windows). Also add a censoring-fixed version of the existing chart to isolate the impact of censoring vs windowing. Add an unsmoothed "Opened per day" chart using the same weekly buckets.

## Charts and placement
- Keep existing "Closed within 2 days" chart unchanged.
- Add "Closed within 2 days (censoring-fixed)" immediately below it.
- Add "Closed within 2 days (weekly buckets)" immediately below that.
- Keep existing "Opened per day" chart unchanged.
- Add "Opened per day (weekly buckets)" immediately below it.

## Components
- New weekly window builder: non-overlapping 7-day windows ending yesterday.
- New survival curve helper that accepts a censor date (window end).
- New aggregation for weekly "Opened per day" chart.
- Minimum PR count threshold for windows (start with 5; revisit later).

## Data flow
1. Load and filter PRs as today.
2. Categorize PRs by created_at date.
3. Build sliding windows (existing) and weekly windows (new).
4. For censoring-fixed charts, build survival curves with censor date = window end.
5. For weekly buckets, aggregate counts or probabilities per bucket and render via XMR charts.

## Edge cases
- Skip windows with fewer than 5 PRs to avoid unstable estimates and XMR distortion (note: tune later).
- If filtering leaves fewer than 2 datapoints, skip rendering the chart or render empty (no misleading limits).
- Weekly windows end at yesterday; if insufficient data, yield no buckets.

## Testing
- Unit tests for weekly window builder (non-overlapping, end at yesterday).
- Unit tests for censoring behavior in survival curve helper (window end vs END_DATE).
- Tests for weekly "Opened per day" aggregation.
- Tests for minimum PR threshold behavior.
- Run targeted test suite and confirm green.
