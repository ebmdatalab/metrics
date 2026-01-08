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
ONE_DAY = datetime.timedelta(days=1)
ONE_WEEK = datetime.timedelta(weeks=1)

DEFAULT_WIDTH = 600
DEFAULT_HEIGHT = 150
SCATTER_HEIGHT = 300
PROB_HEIGHT = 300

START_DATE = datetime.date(2021, 1, 1)
END_DATE = datetime.date.today()


def display():
    all_prs = load_prs()

    interesting_prs = [
        pr
        for pr in all_prs
        if pr.created_at.date() > START_DATE
        and "dependabot" not in pr.author
        and not pr.is_draft
        and not pr.is_content
    ]
    unabandoned_prs = [pr for pr in interesting_prs if not pr.was_abandoned()]

    windows = build_windows(START_DATE, END_DATE, length_days=WINDOW_DAYS)

    prs_open_by_day, prs_opened_by_day = categorise_prs(unabandoned_prs)

    write_charts(
        scatter_chart(interesting_prs),
        count_chart("Opened per day", prs_opened_by_day, windows),
        count_chart("Open at end of day", prs_open_by_day, windows),
        two_day_chart(prs_opened_by_day, windows),
        team_two_day_chart(prs_opened_by_day, windows),
        probabilities_chart(prs_opened_by_day, windows),
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
                axis=altair.Axis(values=[1, 2, 5, 10, 20, 50, 100, 200, 500]),
                title="Age (days)",
            ).scale(type="symlog"),
            color=altair.Color("category:N", legend=altair.Legend(title="Outcome")),
        )
    )


def count_chart(title, prs, windows):
    count_data = list()

    for window in windows:
        window_counts = list()
        for day in window.days():
            window_counts.append(len(prs[day]))
        count_data.append(datapoint(window.end, count=statistics.mean(window_counts)))

    return xmr_chart_from_series(
        count_data,
        value_field="count",
        y_title=title,
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


def two_day_chart(prs, windows):
    probabilities_data = []
    for window in windows:
        prob_of_survival = build_survival_curve(prs, window)
        prob_closed_within_two_days = 1 - prob_of_survival(2)
        probabilities_data.append(
            datapoint(window.end, value=prob_closed_within_two_days)
        )

    return xmr_chart_from_series(
        probabilities_data,
        value_field="value",
        y_title="Closed within 2 days",
    )


def team_two_day_chart(day_to_prs, windows):
    team_to_day_to_prs = defaultdict(lambda: defaultdict(list))
    for day, day_prs in day_to_prs.items():
        for pr in day_prs:
            if pr.repo.team == "tech-shared":
                continue
            team_to_day_to_prs[pr.repo.team][day].append(pr)

    series = []
    for window in windows:
        for team, day_to_team_prs in team_to_day_to_prs.items():
            prob_of_survival = build_survival_curve(day_to_team_prs, window)
            prob_closed_within_two_days = 1 - prob_of_survival(2)
            series.append(
                datapoint(
                    window.end,
                    value=prob_closed_within_two_days,
                    team=team,
                )
            )

    return (
        altair.Chart(
            altair.Data(values=series), width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT
        )
        .mark_line()
        .encode(
            x=altair.X(
                "date:T",
                title=None,
                axis=altair.Axis(format="%Y", tickCount="year"),
            ),
            y=altair.Y("value:Q", title="Closed within 2 days"),
            color=altair.Color("team:N", legend=altair.Legend(title="Team")),
        )
    )


def xmr_chart_from_series(data, value_field, y_title):
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
            y=altair.Y(f"{value_field}:Q", title=y_title),
        ),
        altair.Chart(altair.Data(values=limits))
        .mark_rule(strokeDash=[4, 4])
        .encode(
            y=altair.Y("limit:Q", title=y_title),
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


def write_charts(*charts):
    combined = (
        altair.vconcat(*charts)
        .resolve_scale(color="independent")
        .configure_axis(labelFontSize=18, titleFontSize=18)
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
        end -= ONE_WEEK

    return list(reversed(windows))
