import datetime
import itertools
import statistics

import altair
import numpy
import sksurv.nonparametric

from metrics.github.github import tech_prs


WINDOW_WEEKS = 6
WINDOW_DAYS = WINDOW_WEEKS * 7
WINDOW_WORKDAYS = WINDOW_WEEKS * 5

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

    write_charts(
        scatter_chart(interesting_prs),
        opened_chart(unabandoned_prs, windows),
        queue_length_chart(unabandoned_prs, windows),
        probabilities_chart(unabandoned_prs, windows),
    )


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


def queue_length_chart(prs, windows):
    queue_data = list()

    for window_start_exc, window_end_inc in windows:
        queue_sizes = []
        day = window_start_exc + datetime.timedelta(days=1)
        while (day := day + datetime.timedelta(days=1)) <= window_end_inc:
            queue_sizes.append(len([pr for pr in prs if pr.was_open_at_end_of(day)]))
        queue_data.append(datapoint(window_end_inc, count=statistics.mean(queue_sizes)))

    return (
        altair.Chart(altair.Data(values=queue_data), width=600, height=100)
        .mark_line()
        .encode(
            x=altair.X("date:T", title=f"{WINDOW_WEEKS}-week window end"),
            y=altair.Y("count:Q", title="Open at end of day"),
        )
    )


def opened_chart(prs, windows):
    opened_count_data = list()

    for window_start, window_end in windows:
        window_prs = [
            pr for pr in prs if pr.was_opened_in_period(window_start, window_end)
        ]
        opened_per_workday = len(window_prs) / WINDOW_WORKDAYS
        opened_count_data.append(datapoint(window_end, count=opened_per_workday))

    return (
        altair.Chart(altair.Data(values=opened_count_data), width=600, height=100)
        .mark_line()
        .encode(
            x=altair.X("date:T", title=f"{WINDOW_WEEKS}-week window end"),
            y=altair.Y("count:Q", title="Opened per week day"),
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
    for pr in prs:
        if pr.was_opened_in_period(window_start, window_end):
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
    window_start_exclusive = start_date - datetime.timedelta(days=1)

    windows = []
    while (window_end_inclusive := window_start_exclusive + window_size) <= end_date:
        windows.append((window_start_exclusive, window_end_inclusive))
        window_start_exclusive += datetime.timedelta(days=1)
    return windows


if __name__ == "__main__":
    main()
