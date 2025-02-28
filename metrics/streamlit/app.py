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
        altair.Chart(altair.Data(values=scatter_data), width=600, height=200)
        .mark_circle()
        .encode(
            x=altair.X("date:T", title="Date opened"),
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

    return (
        altair.Chart(altair.Data(values=count_data), width=600, height=100)
        .mark_line()
        .encode(
            x=altair.X("date:T", title=f"{WINDOW_WEEKS}-week window end"),
            y=altair.Y("count:Q", title=title),
        )
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
        altair.Chart(altair.Data(values=probabilities_data), width=600, height=200)
        .mark_area()
        .encode(
            x=altair.X("date:T", title=f"{WINDOW_WEEKS}-week window end"),
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
    st.altair_chart(altair.vconcat(*charts).resolve_scale(color="independent"))


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
        end -= ONE_DAY

    return list(reversed(windows))
