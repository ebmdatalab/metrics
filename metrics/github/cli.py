import itertools
import os
from datetime import UTC, date, datetime, time, timedelta

import click
import structlog

from .. import timescaledb
from ..tools.dates import iter_days, previous_weekday
from . import api
from .prs import drop_archived_prs, iter_prs


log = structlog.get_logger()


def old_prs(prs, org, days_threshold):
    """
    Track "old" PRs

    Defined as: How many PRs had been open for the given days threshold at a
    given sample point?

    We're using Monday morning here to match how the values in throughput are
    bucketed with timeseriesdb's time_bucket() function

    So we start with the Monday before the earliest PR, then iterate from that
    Monday to todays date, filtering the list of PRs down to just those open on
    the given Monday morning.
    """
    earliest = min([pr["created_at"] for pr in prs]).date()
    start = previous_weekday(earliest, 0)  # Monday
    mondays = list(iter_days(start, date.today(), step=timedelta(days=7)))

    the_future = datetime(9999, 1, 1, tzinfo=UTC)
    threshold = timedelta(days=days_threshold)

    def is_old(pr, dt):
        """
        Filter function for PRs

        Checks whether a PR was open at the given datetime, and if it has been
        open long enough.
        """
        closed = pr["closed_at"] or the_future
        opened = pr["created_at"]

        open_now = opened < dt < closed
        if not open_now:
            return False

        return (closed - opened) >= threshold

    for monday in mondays:
        dt = datetime.combine(monday, time(), tzinfo=UTC)
        valid_prs = [pr for pr in prs if is_old(pr, dt)]
        valid_prs = drop_archived_prs(valid_prs, monday)

        name = f"queue_older_than_{days_threshold}_days"

        log.info(
            "%s | %s | Processing %s old PRs at %s",
            name,
            org,
            len(valid_prs),
            dt,
        )
        yield from iter_prs(valid_prs, monday, name)


def pr_throughput(prs, org):
    """
    PRs closed each day from the earliest day to today
    """
    start = min([pr["created_at"] for pr in prs]).date()
    days = list(iter_days(start, date.today()))

    for day in days:
        valid_prs = drop_archived_prs(prs, day)
        merged_prs = [
            pr for pr in valid_prs if pr["merged_at"] and pr["merged_at"].date() == day
        ]

        log.info("%s | %s | Processing %s merged PRs", day, org, len(merged_prs))
        yield from iter_prs(merged_prs, day, name="prs_merged")


NON_TECH_REPOS = {
    "ebmdatalab": [
        "bennett-presentations",
        "bnf-code-to-dmd",
        "change_detection",
        "copiloting",
        "clinicaltrials-act-converter",
        "clinicaltrials-act-tracker",
        "copiloting-publication",
        "datalab-jupyter",
        "dmd-hosp-only",
        "euctr-tracker-code",
        "funding-applications",
        "funding-report",
        "ghost_branded_generics_paper",
        "global-trial-landscape",
        "imagemagick-magick",
        "improvement_radar_prototype",
        "jupyter-notebooks",
        "kurtosis-pericyazine",
        "lidocaine-eng-ire",
        "low-priority-CCG-visit-RCT",
        "nsaid-covid-codelist-notebook",
        "opencorona-sandpit-for-fizz",
        "opensafely-output-review",
        "open-nhs-hospital-use-data",
        "opioids-change-detection-notebook",
        "outliers",
        "prescribing-queries",
        "price-concessions-accuracy-notebook",
        "priceshocks",
        "propaganda",
        "publications",
        "publications-copiloted",
        "retracted.net",
        "retractobot",
        "retractobot-archive",
        "rx-cost-item-analysis",
        "Rx-Quantity-for-Long-Term-Conditions",
        "Rx-Quantity-for-LTCs-notebook",
        "scmd-narcolepsy",
        "seb-test-notebook",
        "service-analytics-team",
        "teaching_resource",
        "trialstracker",
        "vaccinations-covid-codelist-notebook",
    ],
    "opensafely-core": [
        "matching",
        "scribe",
    ],
}


def tech_owned_repo(pr):
    # We use a deny-list rather than an allow-list so that newly created repos are treated as
    # Tech-owned by default, in the hopes of minimizing surprise.
    return not (pr["org"] in NON_TECH_REPOS and pr["repo"] in NON_TECH_REPOS[pr["org"]])


@click.command()
@click.pass_context
def github(ctx):
    ctx.ensure_object(dict)

    timescaledb.reset_table(timescaledb.GitHubPullRequests)

    orgs = {
        "ebmdatalab": os.environ["GITHUB_EBMDATALAB_TOKEN"],
        "opensafely-core": os.environ["GITHUB_OS_CORE_TOKEN"],
    }

    for org, token in orgs.items():
        log.info("Working with org: %s", org)
        client = api.GitHubClient(org, token)

        prs = api.iter_prs(client)
        prs = list(filter(tech_owned_repo, prs))

        log.info("Backfilling with %s PRs for %s", len(prs), org)

        rows = itertools.chain(
            old_prs(prs, org, days_threshold=7),
            pr_throughput(prs, org),
        )

        timescaledb.write(timescaledb.GitHubPullRequests, rows)
