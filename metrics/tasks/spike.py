import datetime
import itertools

import altair
import lifelines
import numpy
from matplotlib import pyplot as plt

from metrics.github.github import tech_prs


def main():
    prs = tech_prs()
    pr_metrics(prs)


def kaplan_meier_chart(prs, buckets):
    kmf = lifelines.KaplanMeierFitter()

    observations = dict()
    for bucket_start, bucket_end in buckets:
        durations = []
        events = []

        for pr in prs:
            if pr.was_opened_in_period(bucket_start, bucket_end):
                if pr.merged_on:
                    durations.append(pr.age_on(pr.merged_on).days)
                    events.append(True)
                elif pr.closed_on:
                    # Ignore abandoned PRs
                    pass
                else:
                    durations.append(pr.age_on(datetime.date.today()).days)
                    events.append(False)

        observations[bucket_end.isoformat()] = (durations, events)

    for bucket, (durations, events) in observations.items():
        kmf.fit(durations, events, label=bucket)

    fig = plt.figure()
    axes = fig.add_axes([0, 0, 1, 1])
    kmf.plot_survival_function(ax=axes)
    plt.savefig("km.png")


def pr_metrics(prs):
    prs = [pr for pr in prs if not pr.is_content and "dependabot" not in pr.author]
    earliest = min(pr.created_on for pr in prs)
    buckets = build_buckets(earliest, days=28)

    kaplan_meier_chart(prs, buckets)

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
        .encode(x="date:T", y=altair.Y("value:Q").scale(type="symlog"))
    )
    quantile_chart = (
        altair.Chart(altair.Data(values=quantile_data), width=600, height=200)
        .mark_line()
        .encode(
            x="date:T",
            y=altair.Y("value:Q").scale(type="symlog"),
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
