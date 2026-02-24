import datetime
import itertools
import statistics
from collections import defaultdict
from dataclasses import dataclass

import altair
import numpy
import sksurv.nonparametric
import streamlit as st

from metrics.github.github import tech_prs
from metrics.tools import dates


WEEKLY_BUCKET_DAYS = 21
ONE_DAY = datetime.timedelta(days=1)

DEFAULT_WIDTH = 600
DEFAULT_HEIGHT = 150
SCATTER_HEIGHT = 300
LABEL_WIDTH = 60
AXIS_LABEL_COLOR = "#6b6b6b"

START_DATE = datetime.date(2021, 1, 1)

SPC_RULE_RUN_8_SAME_SIDE = "8 consecutive on same side of mean"
SPC_RULE_TREND_6 = "6 consecutive increasing/decreasing"
SPC_RULE_POINT_BEYOND_LIMITS = "point beyond control limits"
SPC_RULE_2_OF_3_BEYOND_2SIGMA = "2 of 3 beyond 2 sigma on same side"
SPC_RULE_4_OF_5_BEYOND_1SIGMA = "4 of 5 beyond 1 sigma on same side"
SPC_RULE_15_WITHIN_1SIGMA = "15 consecutive within 1 sigma"
SPC_RULE_8_OUTSIDE_1SIGMA = "8 consecutive outside 1 sigma"
SPC_RULE_14_ALTERNATING = "14 consecutive alternating up/down"
SPC_RULE_8_NO_ZONE_C_BOTH_SIDES = "8 consecutive with no zone C and both sides"


def display():
    today = datetime.date.today()
    all_prs = load_prs()

    interesting_prs = [
        pr
        for pr in all_prs
        if pr.created_at.date() > START_DATE
        and "dependabot" not in pr.author
        and "opensafely-core-create-pr" not in pr.author
        and not pr.is_draft
        and not pr.is_content
    ]
    unabandoned_prs = [pr for pr in interesting_prs if not pr.was_abandoned()]

    weekly_windows = build_weekly_windows(START_DATE, today - ONE_DAY)

    prs_open_by_day, prs_opened_by_day = categorise_prs(unabandoned_prs, today=today)

    write_charts(
        with_y_label(
            scatter_chart(interesting_prs, today),
            "Age (days)",
            SCATTER_HEIGHT,
        ),
        with_y_label(
            count_chart("Opened per day", prs_opened_by_day, weekly_windows),
            "Opened per day",
            DEFAULT_HEIGHT,
        ),
        with_y_label(
            count_chart("Open at end of day", prs_open_by_day, weekly_windows),
            "Open at end of day",
            DEFAULT_HEIGHT,
        ),
        with_y_label(
            closed_within_days_chart(prs_opened_by_day, weekly_windows, days=2),
            "Closed within 2 days",
            DEFAULT_HEIGHT,
        ),
    )


@st.cache_data
def load_prs():
    return tech_prs()


def categorise_prs(unabandoned_prs, today):
    prs_opened_by_day = defaultdict(list)
    prs_open_by_day = defaultdict(list)

    for pr in unabandoned_prs:
        prs_opened_by_day[pr.created_at.date()].append(pr)

        if pr.was_closed():
            end = pr.closed_at.date() - ONE_DAY
        else:
            end = today - ONE_DAY

        for day in dates.iter_days(pr.created_at.date(), end):
            prs_open_by_day[day].append(pr)

    return prs_open_by_day, prs_opened_by_day


def scatter_chart(prs, today):
    scatter_data = list()
    for pr in prs:
        if not pr.was_closed():
            category = "open"
            age = pr.age_at_end_of(today)
        elif pr.was_abandoned():
            category = "abandoned"
            age = pr.age_when_closed()
        else:
            category = "merged"
            age = pr.age_when_merged()
        scatter_data.append(datapoint(pr.created_at, value=age, category=category))

    return (
        altair.Chart(
            altair.Data(values=scatter_data), width=DEFAULT_WIDTH, height=SCATTER_HEIGHT
        )
        .mark_circle()
        .encode(
            x=altair.X(
                "date:T",
                title="Date opened",
                axis=altair.Axis(format="%Y", tickCount="year"),
            ),
            y=altair.Y(
                "value:Q",
                # Setting explict tick values because of a bug: https://github.com/vega/vega/issues/2914
                axis=altair.Axis(
                    values=[1, 2, 5, 10, 20, 50, 100, 200, 500],
                    titleY=SCATTER_HEIGHT / 2,
                    titleBaseline="middle",
                    titleAnchor="middle",
                ),
                title=None,
            ).scale(type="symlog"),
            color=altair.Color("category:N", legend=altair.Legend(title="Outcome")),
        )
    )


def count_chart(title, prs, windows):
    count_data = window_count_datapoints(prs, windows)

    return xmr_chart_from_series(
        count_data,
        value_field="count",
        y_label=title,
    )


def window_count_datapoints(prs, windows):
    count_data = []

    for window in windows:
        window_counts = [len(prs.get(day, [])) for day in window.days()]
        count_data.append(datapoint(window.end, count=statistics.mean(window_counts)))

    return count_data


def closed_within_days_chart(prs, windows, days):
    probabilities_data = closed_within_days_datapoints(prs, windows, days)
    return xmr_chart_from_series(
        probabilities_data,
        value_field="value",
        y_label=f"Closed within {days} days",
    )


def closed_within_days_datapoints(prs, windows, days):
    probabilities_data = []
    for window in windows:
        prob_of_survival = build_survival_curve_with_censor_date(
            prs, window, window.end
        )
        prob_closed_within_days = 1 - prob_of_survival(days)
        probabilities_data.append(datapoint(window.end, value=prob_closed_within_days))

    return probabilities_data


def xmr_chart_from_series(data, value_field, y_label):
    assert len(data) >= 2, "xmr_chart_from_series requires at least 2 datapoints"
    assert all(
        value_field in item for item in data
    ), f"xmr_chart_from_series data missing field {value_field!r}"
    values = [item[value_field] for item in data]
    moving_ranges = [abs(curr - prev) for prev, curr in itertools.pairwise(values)]
    mean = statistics.mean(values)
    mean_mr = statistics.mean(moving_ranges)
    ucl = mean + 2.66 * mean_mr
    lcl = mean - 2.66 * mean_mr
    signal_rules_by_point = detect_spc_signals(values, mean=mean, ucl=ucl, lcl=lcl)
    annotated_data = []
    for item, signal_rules in zip(data, signal_rules_by_point):
        annotated_data.append(
            {
                **item,
                "signal": bool(signal_rules),
                "signal_rules": ", ".join(sorted(signal_rules)),
            }
        )

    limits = [
        {"limit": lcl, "label": "LCL"},
        {"limit": mean, "label": "Mean"},
        {"limit": ucl, "label": "UCL"},
    ]

    return altair.layer(
        altair.Chart(
            altair.Data(values=annotated_data),
            width=DEFAULT_WIDTH,
            height=DEFAULT_HEIGHT,
        )
        .mark_line(color="#4c78a8")
        .encode(
            x=altair.X(
                "date:T",
                title=None,
                axis=altair.Axis(format="%Y", tickCount="year"),
            ),
            y=altair.Y(
                f"{value_field}:Q",
                title=None,
                axis=altair.Axis(
                    titleY=DEFAULT_HEIGHT / 2,
                    titleBaseline="middle",
                    titleAnchor="middle",
                    labelFlush=False,
                ),
            ),
            tooltip=[
                altair.Tooltip(
                    "date:T",
                    title="Bucket end",
                    format="%d %b %Y",
                ),
                altair.Tooltip(
                    f"{value_field}:Q",
                    title=y_label,
                    format=".3f",
                ),
                altair.Tooltip(
                    "signal_rules:N",
                    title="SPC signals",
                ),
            ],
        ),
        altair.Chart(altair.Data(values=annotated_data))
        .mark_point(color="#e45756", size=60, filled=True)
        .transform_filter("datum.signal")
        .encode(
            x=altair.X("date:T", title=None),
            y=altair.Y(f"{value_field}:Q", title=None),
            tooltip=[
                altair.Tooltip(
                    "date:T",
                    title="Bucket end",
                    format="%d %b %Y",
                ),
                altair.Tooltip(
                    f"{value_field}:Q",
                    title=y_label,
                    format=".3f",
                ),
                altair.Tooltip(
                    "signal_rules:N",
                    title="SPC signals",
                ),
            ],
        ),
        altair.Chart(altair.Data(values=limits))
        .mark_rule(strokeDash=[4, 4])
        .encode(
            y=altair.Y("limit:Q", title=None),
            color=altair.Color(
                "label:N",
                legend=None,
                scale=altair.Scale(
                    domain=["Mean", "LCL", "UCL"],
                    range=["#4c78a8", "#a3c5f4", "#a3c5f4"],
                ),
            ),
        ),
    ).resolve_scale(color="independent")


def detect_spc_signals(values, mean, ucl, lcl):
    signals = [set() for _ in values]
    _mark_points_beyond_limits(values, ucl, lcl, signals)
    _mark_run_of_8_same_side(values, mean, signals)
    _mark_trend_of_6(values, signals)
    sigma = (ucl - mean) / 3
    if sigma > 0:
        _mark_2_of_3_beyond_2sigma(values, mean, sigma, signals)
        _mark_4_of_5_beyond_1sigma(values, mean, sigma, signals)
        _mark_15_within_1sigma(values, mean, sigma, signals)
        _mark_8_outside_1sigma(values, mean, sigma, signals)
        _mark_8_no_zone_c_both_sides(values, mean, sigma, signals)
    _mark_14_alternating(values, signals)
    return signals


def _mark_points_beyond_limits(values, ucl, lcl, signals):
    for index, value in enumerate(values):
        if value > ucl or value < lcl:
            signals[index].add(SPC_RULE_POINT_BEYOND_LIMITS)


def _mark_run_of_8_same_side(values, mean, signals):
    run_sign = 0
    run_start = 0

    for index, value in enumerate(values):
        sign = 1 if value > mean else -1 if value < mean else 0
        if sign == 0:
            run_sign = 0
            run_start = index + 1
            continue

        if sign != run_sign:
            run_sign = sign
            run_start = index

        if index - run_start + 1 >= 8:
            for marked_index in range(run_start, index + 1):
                signals[marked_index].add(SPC_RULE_RUN_8_SAME_SIDE)


def _mark_trend_of_6(values, signals):
    increasing_start = 0
    decreasing_start = 0

    for index in range(1, len(values)):
        if values[index] > values[index - 1]:
            if index == 1 or values[index - 1] <= values[index - 2]:
                increasing_start = index - 1

            if index - increasing_start + 1 >= 6:
                for marked_index in range(increasing_start, index + 1):
                    signals[marked_index].add(SPC_RULE_TREND_6)
        elif values[index] < values[index - 1]:
            if index == 1 or values[index - 1] >= values[index - 2]:
                decreasing_start = index - 1

            if index - decreasing_start + 1 >= 6:
                for marked_index in range(decreasing_start, index + 1):
                    signals[marked_index].add(SPC_RULE_TREND_6)


def _mark_2_of_3_beyond_2sigma(values, mean, sigma, signals):
    threshold = 2 * sigma
    for start in range(len(values) - 2):
        window_indexes = range(start, start + 3)
        above_indexes = [i for i in window_indexes if values[i] > mean + threshold]
        below_indexes = [i for i in window_indexes if values[i] < mean - threshold]
        if len(above_indexes) >= 2:
            for index in above_indexes:
                signals[index].add(SPC_RULE_2_OF_3_BEYOND_2SIGMA)
        if len(below_indexes) >= 2:
            for index in below_indexes:
                signals[index].add(SPC_RULE_2_OF_3_BEYOND_2SIGMA)


def _mark_4_of_5_beyond_1sigma(values, mean, sigma, signals):
    for start in range(len(values) - 4):
        window_indexes = range(start, start + 5)
        above_indexes = [i for i in window_indexes if values[i] > mean + sigma]
        below_indexes = [i for i in window_indexes if values[i] < mean - sigma]
        if len(above_indexes) >= 4:
            for index in above_indexes:
                signals[index].add(SPC_RULE_4_OF_5_BEYOND_1SIGMA)
        if len(below_indexes) >= 4:
            for index in below_indexes:
                signals[index].add(SPC_RULE_4_OF_5_BEYOND_1SIGMA)


def _mark_15_within_1sigma(values, mean, sigma, signals):
    for start in range(len(values) - 14):
        window_indexes = list(range(start, start + 15))
        if all(abs(values[i] - mean) < sigma for i in window_indexes):
            for index in window_indexes:
                signals[index].add(SPC_RULE_15_WITHIN_1SIGMA)


def _mark_8_outside_1sigma(values, mean, sigma, signals):
    run_start = 0
    run_length = 0
    for index, value in enumerate(values):
        if abs(value - mean) > sigma:
            if run_length == 0:
                run_start = index
            run_length += 1
            if run_length >= 8:
                for marked_index in range(run_start, index + 1):
                    signals[marked_index].add(SPC_RULE_8_OUTSIDE_1SIGMA)
        else:
            run_length = 0


def _mark_14_alternating(values, signals):
    for start in range(len(values) - 13):
        window = values[start : start + 14]
        deltas = [curr - prev for prev, curr in itertools.pairwise(window)]
        if any(delta == 0 for delta in deltas):
            continue
        if all(prev * curr < 0 for prev, curr in itertools.pairwise(deltas)):
            for index in range(start, start + 14):
                signals[index].add(SPC_RULE_14_ALTERNATING)


def _mark_8_no_zone_c_both_sides(values, mean, sigma, signals):
    for start in range(len(values) - 7):
        window_indexes = list(range(start, start + 8))
        window_values = [values[i] for i in window_indexes]
        if not all(abs(value - mean) > sigma for value in window_values):
            continue
        has_above = any(value > mean for value in window_values)
        has_below = any(value < mean for value in window_values)
        if has_above and has_below:
            for index in window_indexes:
                signals[index].add(SPC_RULE_8_NO_ZONE_C_BOTH_SIDES)


def y_label_chart(label, height):
    return (
        altair.Chart(altair.Data(values=[{}]), width=LABEL_WIDTH, height=height)
        .mark_text(
            angle=270,
            align="center",
            baseline="middle",
            fontSize=18,
            color=AXIS_LABEL_COLOR,
        )
        .encode(text=altair.value(label))
    )


def with_y_label(chart, label, height):
    return altair.hconcat(y_label_chart(label, height), chart, spacing=5)


def build_survival_curve_with_censor_date(prs, window, censor_date):
    observation_flags = []
    durations = []

    for day in window.days():
        for pr in prs[day]:
            if pr.was_merged():
                observation_flags.append(True)
                durations.append(working_days_between(pr.created_at, pr.merged_at))
            else:
                observation_flags.append(False)
                end_midnight = datetime.time(0, 0, 0, tzinfo=pr.created_at.tzinfo)
                censor_end = datetime.datetime.combine(
                    censor_date + ONE_DAY, end_midnight
                )
                durations.append(working_days_between(pr.created_at, censor_end))

    times, probs = sksurv.nonparametric.kaplan_meier_estimator(
        observation_flags, durations
    )

    def prob_of_surviving_for_days(days):
        if days == 0:
            return 1.0
        return numpy.interp([days], times, probs)[0]

    return prob_of_surviving_for_days


def working_days_between(start, end):
    if end <= start:
        return 0.0

    total_seconds = 0.0
    current = start
    while current.date() <= end.date():
        day_start = datetime.datetime.combine(
            current.date(), datetime.time(0, 0, 0, tzinfo=current.tzinfo)
        )
        day_end = day_start + ONE_DAY

        segment_start = max(current, day_start)
        segment_end = min(end, day_end)

        if segment_start < segment_end and segment_start.weekday() < 5:
            total_seconds += (segment_end - segment_start).total_seconds()

        current = day_end

    return total_seconds / ONE_DAY.total_seconds()


def write_charts(*charts):
    combined = (
        altair.vconcat(*charts)
        .resolve_scale(color="independent")
        .configure_axis(
            labelFontSize=18,
            titleFontSize=18,
            labelColor=AXIS_LABEL_COLOR,
            titleColor=AXIS_LABEL_COLOR,
        )
        .configure_axisY(titleAlign="left", titleX=-60, titlePadding=10)
        .configure_legend(labelFontSize=18, titleFontSize=18)
        .configure_title(fontSize=18)
    )
    st.altair_chart(combined, use_container_width=False)


def datapoint(date, **kwargs):
    return dict(date=date.isoformat(), **kwargs)


@dataclass
class Window:
    start: datetime.date  # exclusive
    end: datetime.date  # inclusive

    def days(self):
        return dates.iter_days(self.start + ONE_DAY, self.end)


def build_weekly_windows(start_date, end_date):
    window_size = datetime.timedelta(days=WEEKLY_BUCKET_DAYS)

    windows = []
    end = end_date
    while (start := end - window_size) >= start_date:
        windows.append(Window(start, end))
        end -= window_size

    return list(reversed(windows))
