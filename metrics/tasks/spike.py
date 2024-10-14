import datetime
import itertools

import altair
import numpy
import sksurv.nonparametric

from metrics.github.github import tech_prs


# TODO
#   - maybe speed up by building look-up table dates -> windows

WINDOW_WEEKS = 4
WINDOW_DAYS = WINDOW_WEEKS * 7
WINDOW_WORKDAYS = WINDOW_WEEKS * 5
WINDOW_STEP = 2

START_DATE = datetime.date(2021, 1, 1)
END_DATE = datetime.date.today()


def main():
    prs = tech_prs()

    prs = [
        pr for pr in prs if pr.created_on > START_DATE and "dependabot" not in pr.author
    ]

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
        scatter_data.append(datapoint(pr.created_on, value=age.days, category=category))

    scatter_chart = (
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

    # We exclude PRs that were eventually abandoned from the remainder of the analysis
    prs = [pr for pr in prs if not pr.was_abandoned()]

    windows = build_windows(START_DATE, END_DATE, length_days=WINDOW_DAYS)

    opened_count_data = list()
    for window_start, window_end in windows:
        window_count = len(
            [pr for pr in prs if pr.was_opened_in_period(window_start, window_end)]
        )
        count = window_count / WINDOW_WORKDAYS
        opened_count_data.append(datapoint(window_end, count=count))

    opened_count_chart = (
        altair.Chart(altair.Data(values=opened_count_data), width=600, height=100)
        .mark_line()
        .encode(
            x=altair.X("date:T", title="Window end"),
            y=altair.Y("count:Q", title="Opened per week day"),
        )
    )

    queue_data = list()
    for window_start, window_end in windows:
        count = len([pr for pr in prs if pr.was_open_at_end_of(window_end)])
        queue_data.append(datapoint(window_end, count=count))

    queue_length_chart = (
        altair.Chart(altair.Data(values=queue_data), width=600, height=100)
        .mark_line()
        .encode(
            x=altair.X("date:T", title="Window end"),
            y=altair.Y("count:Q", title="Number open"),
        )
    )

    quantile_chart, probabilities_chart = kaplan_meier_charts(prs, windows)

    altair.vconcat(
        scatter_chart,
        opened_count_chart,
        queue_length_chart,
        quantile_chart,
        probabilities_chart,
    ).resolve_scale(color="independent").save("prs.html")


def kaplan_meier_charts(prs, windows):
    quantile_data = []
    probabilities_data = []
    for window_start, window_end in windows:
        observation_flags = []
        durations = []

        for pr in prs:
            if pr.was_opened_in_period(window_start, window_end):
                if pr.was_merged():
                    # Uncensored observation
                    observation_flags.append(True)
                    durations.append(pr.age_when_merged().days)
                else:
                    # Censored observation
                    observation_flags.append(False)
                    durations.append(pr.age_on(datetime.date.today()).days)

        survival_times, survival_probs = sksurv.nonparametric.kaplan_meier_estimator(
            observation_flags, durations
        )

        cum_probs = [1.0 - p for p in survival_probs]

        for quantile in itertools.chain(range(10, 100, 10)):
            probability = quantile / 100.0
            survival_time = numpy.interp([probability], cum_probs, survival_times)[0]
            quantile_data.append(
                datapoint(window_end, quantile=f"p{quantile}", value=survival_time)
            )

        for days in [0, 2, 7, 14, 28]:
            prob = numpy.interp([days], survival_times, cum_probs)[0]
            probabilities_data.append(datapoint(window_end, days=days, value=prob))

    quantile_chart = (
        altair.Chart(altair.Data(values=quantile_data), width=600, height=200)
        .mark_line()
        .encode(
            x=altair.X("date:T", title="Window end"),
            y=altair.Y(
                "value:Q",
                # Setting explict tick values because of a bug: https://github.com/vega/vega/issues/2914
                axis=altair.Axis(values=[1, 2, 5, 10, 20, 50]),
                title="Age (days)",
            ).scale(type="symlog"),
            color=altair.Color("quantile:N", legend=altair.Legend(title="Deciles")),
        )
    )

    probabilities_chart = (
        altair.Chart(altair.Data(values=probabilities_data), width=600, height=200)
        .mark_line()
        .encode(
            x=altair.X("date:T", title="Window end"),
            y=altair.Y("value:Q", title="Proportion closed within..."),
            color=altair.Color("days:N", legend=altair.Legend(title="Number of days")),
        )
    )

    return quantile_chart, probabilities_chart


def datapoint(date, **kwargs):
    return dict(date=date.isoformat(), **kwargs)


def build_windows(start_date, end_date, length_days):
    window_size = datetime.timedelta(days=length_days)
    window_start_exclusive = start_date - datetime.timedelta(days=1)

    windows = []
    while (window_end_inclusive := window_start_exclusive + window_size) <= end_date:
        windows.append((window_start_exclusive, window_end_inclusive))
        window_start_exclusive += datetime.timedelta(days=WINDOW_STEP)
    return windows


if __name__ == "__main__":
    main()
