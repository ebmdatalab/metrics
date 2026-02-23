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


WINDOW_WEEKS = 6
WINDOW_DAYS = WINDOW_WEEKS * 7
WEEKLY_BUCKET_DAYS = 21
ONE_DAY = datetime.timedelta(days=1)
ONE_WEEK = datetime.timedelta(weeks=1)

DEFAULT_WIDTH = 600
DEFAULT_HEIGHT = 150
SCATTER_HEIGHT = 300
PROB_HEIGHT = 300
LABEL_WIDTH = 60
AXIS_LABEL_COLOR = "#6b6b6b"

START_DATE = datetime.date(2021, 1, 1)
END_DATE = datetime.date.today()


def display():
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

    windows = build_windows(START_DATE, END_DATE, length_days=WINDOW_DAYS)
    weekly_windows = build_weekly_windows(START_DATE, END_DATE - ONE_DAY)

    prs_open_by_day, prs_opened_by_day = categorise_prs(unabandoned_prs)

    write_charts(
        with_y_label(
            scatter_chart(interesting_prs),
            "Age (days)",
            SCATTER_HEIGHT,
        ),
        with_y_label(
            count_chart_weekly("Opened per day", prs_opened_by_day, weekly_windows),
            "Opened per day",
            DEFAULT_HEIGHT,
        ),
        with_y_label(
            open_end_of_day_chart_weekly(prs_open_by_day, weekly_windows),
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


def categorise_prs(unabandoned_prs):
    prs_opened_by_day = defaultdict(list)
    prs_open_by_day = defaultdict(list)

    for pr in unabandoned_prs:
        prs_opened_by_day[pr.created_at.date()].append(pr)

        if pr.was_closed():
            end = pr.closed_at.date() - ONE_DAY
        else:
            end = datetime.date.today() - ONE_DAY

        for day in dates.iter_days(pr.created_at.date(), end):
            prs_open_by_day[day].append(pr)

    return prs_open_by_day, prs_opened_by_day


def scatter_chart(prs):
    scatter_data = list()
    for pr in prs:
        if not pr.was_closed():
            category = "open"
            age = pr.age_at_end_of(END_DATE)
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


def count_chart_weekly(title, prs, windows):
    count_data = window_count_datapoints(prs, windows)

    return xmr_chart_from_series(
        count_data,
        value_field="count",
        y_label=title,
    )


def open_end_of_day_chart_weekly(prs, windows):
    count_data = window_open_end_of_day_datapoints(prs, windows)

    return xmr_chart_from_series(
        count_data,
        value_field="count",
        y_label="Open at end of day",
    )


def window_count_datapoints(prs, windows, min_prs=None):
    count_data = []

    for window in windows:
        window_counts = [len(prs.get(day, [])) for day in window.days()]
        count_data.append(datapoint(window.end, count=statistics.mean(window_counts)))

    return count_data


def window_open_end_of_day_datapoints(prs, windows, min_prs=None):
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


def probabilities_chart(prs, windows):
    probabilities_data = []
    for window in windows:
        prob_of_survival = build_survival_curve(prs, window)

        for span_start, span_end in itertools.pairwise([0, 1, 3, 7, 14, 28]):
            prob_closed = prob_of_survival(span_start) - prob_of_survival(span_end)
            probabilities_data.append(
                datapoint(window.end, days=span_end, value=prob_closed)
            )

    return (
        altair.Chart(
            altair.Data(values=probabilities_data),
            width=DEFAULT_WIDTH,
            height=PROB_HEIGHT,
        )
        .mark_area()
        .encode(
            x=altair.X(
                "date:T",
                title=None,
                axis=altair.Axis(format="%Y", tickCount="year"),
            ),
            y=altair.Y(
                "value:Q",
                title="Proportion closed within...",
                scale=altair.Scale(domain=[0.0, 1.0]),
            ),
            color=altair.Color(
                "days:O",
                legend=altair.Legend(title="Number of days"),
                sort="descending",
            ),
            order="days:O",
        )
    )


def closed_within_days_datapoints(prs, windows, days):
    probabilities_data = []
    for window in windows:
        prob_of_survival = build_survival_curve_with_censor_date(
            prs, window, window.end
        )
        prob_closed_within_days = 1 - prob_of_survival(days)
        probabilities_data.append(
            datapoint(window.end, value=prob_closed_within_days)
        )

    return probabilities_data


def xmr_chart_from_series(data, value_field, y_label):
    values = [item[value_field] for item in data]
    moving_ranges = [abs(curr - prev) for prev, curr in itertools.pairwise(values)]
    mean = statistics.mean(values)
    mean_mr = statistics.mean(moving_ranges)
    ucl = mean + 2.66 * mean_mr
    lcl = mean - 2.66 * mean_mr

    limits = [
        {"limit": lcl, "label": "LCL"},
        {"limit": mean, "label": "Mean"},
        {"limit": ucl, "label": "UCL"},
    ]

    return altair.layer(
        altair.Chart(
            altair.Data(values=data), width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT
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


def build_survival_curve(prs, window):
    observation_flags = []
    durations = []

    for day in window.days():
        for pr in prs[day]:
            if pr.was_merged():
                # Uncensored observation
                observation_flags.append(True)
                durations.append(pr.age_when_merged())
            else:
                # Censored observation
                observation_flags.append(False)
                durations.append(pr.age_at_end_of(END_DATE))

    times, probs = sksurv.nonparametric.kaplan_meier_estimator(
        observation_flags, durations
    )

    def prob_of_surviving_for_days(days):
        if days == 0:
            return 1.0
        return numpy.interp([days], times, probs)[0]

    return prob_of_surviving_for_days


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
    start: datetime.datetime  # exclusive
    end: datetime.datetime  # inclusive

    def days(self):
        return dates.iter_days(self.start + ONE_DAY, self.end)


def build_windows(start_date, end_date, length_days):
    window_size = datetime.timedelta(days=length_days)

    windows = []
    end = end_date
    while (start := end - window_size) >= start_date:
        windows.append(Window(start, end))
        end -= datetime.timedelta(weeks=4)

    return list(reversed(windows))


def build_weekly_windows(start_date, end_date):
    window_size = datetime.timedelta(days=WEEKLY_BUCKET_DAYS)

    windows = []
    end = end_date
    while (start := end - window_size) >= start_date:
        windows.append(Window(start, end))
        end -= window_size

    return list(reversed(windows))
