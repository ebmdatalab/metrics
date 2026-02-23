# Weekly control chart without smoothing (design)

## Goal
Adopt a simplified, consistent set of weekly (non-overlapping) charts aligned with control analysis. Remove sliding-window charts and auxiliary breakdowns. Keep the scatterplot. Use window-end censoring for the weekly "Closed within 2 days" chart. Add a histogram of weekly PR counts to inform tuning.

## Charts and placement (final order)
1. Scatterplot (unchanged)
2. Opened per day (weekly buckets)
3. Open at end of day (weekly average of daily open-at-end-of-day)
4. Closed within 2 days (weekly buckets, window-end censoring)
5. Histogram of PRs opened per weekly bucket (integer bins, count of buckets)

## Components
- Weekly window builder: non-overlapping 7-day windows ending yesterday.
- Survival curve helper that accepts a censor date (window end).
- Weekly aggregations for:
  - Opened per day (weekly buckets).
  - Open at end of day (weekly average of daily open-at-end-of-day).
  - Closed within 2 days (weekly buckets).
- Weekly bucket totals for histogram (integer bins, count of buckets).
- Minimum PR count threshold for windows (start with 5; revisit later).

## Data flow
1. Load and filter PRs as today.
2. Categorize PRs by created_at date and by open-at-end-of-day.
3. Build weekly windows (non-overlapping, end at yesterday).
4. Aggregate weekly counts/averages for opened-per-day and open-at-end-of-day.
5. For closed-within-2-days, build survival curves with censor date = window end.
6. Render weekly charts via XMR charts.
7. Compute histogram from weekly bucket totals (no min-prs filtering) and render as a bar chart.

## Edge cases
- Skip windows with fewer than 5 PRs to avoid unstable estimates and XMR distortion (note: tune later).
- If filtering leaves fewer than 2 datapoints, render an empty chart (avoid misleading limits).
- Weekly windows end at yesterday; if insufficient data, yield no buckets.

## Testing
- Unit tests for weekly window builder (non-overlapping, end at yesterday).
- Unit tests for censoring behavior in survival curve helper (window end vs END_DATE).
- Tests for weekly "Opened per day" aggregation.
- Tests for weekly "Open at end of day" aggregation.
- Tests for minimum PR threshold behavior.
- Tests for weekly histogram binning (integer bins).
- Run targeted test suite and confirm green.
