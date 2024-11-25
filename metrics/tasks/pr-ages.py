import datetime
import itertools
import statistics

import altair
import numpy
import sksurv.nonparametric

from metrics.github.github import tech_prs
from metrics.tools import dates


WINDOW_WEEKS = 6
WINDOW_DAYS = WINDOW_WEEKS * 7
ONE_DAY = datetime.timedelta(days=1)

START_DATE = datetime.datetime(2021, 1, 1, 0, 0, tzinfo=datetime.UTC)
END_DATE = datetime.datetime.now(tz=datetime.UTC)


def main():
    all_prs = tech_prs()

    interesting_prs = [
        pr
        for pr in all_prs
        if pr.created_on > START_DATE
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


def categorise_prs(unabandoned_prs):
    prs_opened_by_day = dict()
    prs_open_by_day = dict()
    for day in dates.iter_days(START_DATE, END_DATE):
        opened_prs = list()
        open_prs = list()
        for pr in unabandoned_prs:
            if pr.was_opened_on(day):
                opened_prs.append(pr)
            if pr.was_open_at_end_of(day):
                open_prs.append(pr)
        prs_opened_by_day[day] = opened_prs
        prs_open_by_day[day] = open_prs
    return prs_open_by_day, prs_opened_by_day


def scatter_chart(prs):
    scatter_data = list()
    for pr in prs:
        if not pr.was_closed():
            category = "open"
            age = pr.age_on(END_DATE)
        elif pr.was_abandoned():
            category = "abandoned"
            age = pr.age_when_closed()
        else:
            category = "merged"
            age = pr.age_when_merged()
        scatter_data.append(datapoint(pr.created_on, value=age, category=category))

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

    for window_start_exc, window_end_inc in windows:
        window_counts = list()
        for day in dates.iter_days(window_start_exc + ONE_DAY, window_end_inc):
            window_counts.append(len(prs[day]))
        count_data.append(
            datapoint(window_end_inc, count=statistics.mean(window_counts))
        )

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
    for window_start, window_end in windows:
        prob_of_survival = build_survival_curve(prs, window_start, window_end)

        for span_start, span_end in itertools.pairwise([0, 1, 3, 7, 14, 28]):
            prob_closed = prob_of_survival(span_start) - prob_of_survival(span_end)
            probabilities_data.append(
                datapoint(window_end, days=span_end, value=prob_closed)
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


def build_survival_curve(prs, window_start, window_end):
    observation_flags = []
    durations = []

    for day in dates.iter_days(window_start + ONE_DAY, window_end):
        for pr in prs[day]:
            if pr.was_merged():
                # Uncensored observation
                observation_flags.append(True)
                durations.append(pr.age_when_merged())
            else:
                # Censored observation
                observation_flags.append(False)
                durations.append(pr.age_on(END_DATE))

    times, probs = sksurv.nonparametric.kaplan_meier_estimator(
        observation_flags, durations
    )

    def prob_of_surviving_for_days(days):
        if days == 0:
            return 1.0
        return numpy.interp([days], times, probs)[0]

    return prob_of_surviving_for_days


def write_charts(*charts):
    altair.vconcat(*charts).resolve_scale(color="independent").save("prs.html")


def datapoint(date, **kwargs):
    return dict(date=date.isoformat(), **kwargs)


def build_windows(start_date, end_date, length_days):
    window_size = datetime.timedelta(days=length_days)
    window_start_exclusive = start_date - ONE_DAY

    windows = []
    while (window_end_inclusive := window_start_exclusive + window_size) <= end_date:
        windows.append((window_start_exclusive, window_end_inclusive))
        window_start_exclusive += ONE_DAY
    return windows


if __name__ == "__main__":
    main()
