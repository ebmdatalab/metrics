import datetime
import itertools
from pprint import pprint

import altair
import numpy
import sksurv.nonparametric

from metrics.github.github import tech_prs


def main():
    prs = tech_prs()
    pr_metrics(prs)


def kaplan_meier_chart(prs, buckets):
    survival_data = []
    quantile_data = []
    probabilities_data = []
    for bucket_start, bucket_end in buckets:
        observation_flags = []
        durations = []

        for pr in prs:
            if pr.was_opened_in_period(bucket_start, bucket_end):
                if pr.was_abandoned():
                    # We entirely exclude abandoned PRs from the analysis
                    # TODO apply this filter globally, add a chart of abandoned PR numbers
                    pass
                elif pr.was_merged():
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
        survival_times = [int(t) for t in survival_times]
        survival_probs = [float(p) for p in survival_probs]

        for survival_time, survival_prob in zip(survival_times, survival_probs):
            survival_data.append(
                datapoint(bucket_end, days=survival_time, prob=survival_prob)
            )

        cum_probs = list(zip([1. - p for p in survival_probs], survival_times))
        def quantile_calc(prob):
            for obs_prob, time in cum_probs:
                if obs_prob >= prob:
                    return time
            return time
        for quantile in itertools.chain(range(10, 100, 10)):
            quantile_data.append(
                datapoint(
                    bucket_end,
                    quantile=f"p{quantile}",
                    value=quantile_calc(quantile / 100.),
                )
            )

        for latency in [0, 1, 2, 5, 10, 20, 50]:
            prob = numpy.interp([latency], survival_times, survival_probs)[0]
            probabilities_data.append(
                datapoint(bucket_end, latency=f"l{latency}", value=prob)
            )

    survival_chart = (
        altair.Chart(altair.Data(values=survival_data), width=600, height=400)
        .mark_line()
        .encode(
            x=altair.X(
                "days:Q",
                # Setting explict tick values because of a bug: https://github.com/vega/vega/issues/2914
                axis=altair.Axis(values=[1, 2, 5, 10, 20, 50, 100, 200, 500]),
            ).scale(type="symlog"),
            y=altair.Y("prob:Q").scale(type="symlog"),
            color=altair.Color("date:N", scale=altair.Scale(scheme="inferno")),
        )
    )

    quantile_chart = (
        altair.Chart(altair.Data(values=quantile_data), width=600, height=200)
        .mark_line()
        .encode(
            x="date:T",
            y=altair.Y(
                "value:Q",
                # Setting explict tick values because of a bug: https://github.com/vega/vega/issues/2914
                axis=altair.Axis(values=[1, 2, 5, 10, 20, 50, 100, 200, 500]),
            ).scale(type="symlog"),
            detail="quantile:N",
            strokeDash=altair.condition(
                "datum.quantile == 'p50'", altair.value([1, 0]), altair.value([3, 3])
            ),
            strokeOpacity=altair.condition(
                altair.FieldOneOfPredicate(
                    "quantile", ["p92", "p94", "p96", "p98", "p100"]
                ),
                altair.value(0.3),
                altair.value(1.0),
            ),
        )
    )

    probabilities_chart = (
        altair.Chart(altair.Data(values=probabilities_data), width=600, height=200)
        .mark_line()
        .encode(
            x="date:T",
            y=altair.Y(
                "value:Q"
            ).scale(type="symlog"),
            color="latency:N",
        )
    )

    return quantile_chart, probabilities_chart


def pr_metrics(prs):
    prs = [pr for pr in prs if not pr.is_content and "dependabot" not in pr.author]
    buckets = build_buckets(datetime.date.today() - datetime.timedelta(days=800), days=28)

    altair.vconcat(
        *build_charts(
            "open",
            buckets,
            prs,
            lambda pr, bucket: pr.was_open_at_end_of(bucket[1]),
            lambda pr, bucket: pr.age_on(bucket[1]).days,
        ),
        *build_charts(
            "merged",
            buckets,
            prs,
            lambda pr, bucket: pr.was_merged_in_period(bucket[0], bucket[1]),
            lambda pr, bucket: pr.age_on(pr.merged_on).days,
        ),
        *build_charts(
            "opened",
            buckets,
            prs,
            lambda pr, bucket: pr.was_opened_in_period(bucket[0], bucket[1])
            and pr.closed_on,
            lambda pr, bucket: pr.age_on(pr.closed_on).days,
        ),
        *kaplan_meier_chart(prs, buckets),
    ).save("prs.html")


def datapoint(date, **kwargs):
    return dict(date=date.isoformat(), **kwargs)


def build_charts(label, buckets, prs, predicate, calculator):
    count_data = list()
    scatter_data = list()
    quantile_data = list()

    for bucket in buckets:
        (_, bucket_end) = bucket
        values = []
        for pr in prs:
            if predicate(pr, bucket):
                value = calculator(pr, bucket)
                values.append(value)
                scatter_data.append(datapoint(bucket_end, value=value))

        count_data.append(datapoint(bucket_end, count=len(values)))

        if values:
            for quantile in itertools.chain(range(10, 100, 10), range(92, 101, 2)):
                quantile_data.append(
                    datapoint(
                        bucket_end,
                        quantile=f"p{quantile}",
                        value=numpy.quantile(values, q=quantile / 100.0),
                    )
                )

    count_chart = (
        altair.Chart(altair.Data(values=count_data), width=600, height=100)
        .mark_line()
        .encode(x="date:T", y=altair.Y("count:Q", title=label))
    )
    scatter_chart = (
        altair.Chart(altair.Data(values=scatter_data), width=600, height=200)
        .mark_circle()
        .encode(
            x="date:T",
            y=altair.Y(
                "value:Q",
                # Setting explict tick values because of a bug: https://github.com/vega/vega/issues/2914
                axis=altair.Axis(values=[1, 2, 5, 10, 20, 50, 100, 200, 500]),
            ).scale(type="symlog"),
        )
    )
    quantile_chart = (
        altair.Chart(altair.Data(values=quantile_data), width=600, height=200)
        .mark_line()
        .encode(
            x="date:T",
            y=altair.Y(
                "value:Q",
                # Setting explict tick values because of a bug: https://github.com/vega/vega/issues/2914
                axis=altair.Axis(values=[1, 2, 5, 10, 20, 50, 100, 200, 500]),
            ).scale(type="symlog"),
            detail="quantile:N",
            strokeDash=altair.condition(
                "datum.quantile == 'p50'", altair.value([1, 0]), altair.value([3, 3])
            ),
            strokeOpacity=altair.condition(
                altair.FieldOneOfPredicate(
                    "quantile", ["p92", "p94", "p96", "p98", "p100"]
                ),
                altair.value(0.3),
                altair.value(1.0),
            ),
        )
    )

    return count_chart, scatter_chart, quantile_chart


def build_buckets(earliest, days):
    bucket_size = datetime.timedelta(days=days)
    buckets = []
    bucket_end = datetime.date.today()
    while bucket_end >= earliest:
        bucket_start = bucket_end - bucket_size
        buckets.append((bucket_start, bucket_end))
        bucket_end = bucket_start
    return list(reversed(buckets))


if __name__ == "__main__":
    main()
