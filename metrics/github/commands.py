from datetime import timedelta

import structlog

from . import api
from .prs import process_prs


log = structlog.get_logger()


def pr_queue(org, date, days_threshold=None):
    """The number of PRs open on the given date"""
    prs = api.prs_open_on_date(org, date)

    if days_threshold is not None:
        # remove PRs which have been open <days_threshold days
        prs = [
            pr
            for pr in prs
            if (pr["closed"] - pr["created"]) >= timedelta(days=days_threshold)
        ]

    suffix = f"_older_than_{days_threshold}_days" if days_threshold else ""

    log.info("%s | %s | Processing %s PRs", date, org, len(prs))
    process_prs(f"queue{suffix}", prs, date)


def pr_throughput(org, date, days):
    """PRs opened in the last number of days given"""
    start = date - timedelta(days=days)
    end = date

    prs = api.prs_opened_in_the_last_N_days(org, start, end)

    log.info("%s | %s | Processing %s PRs", date, org, len(prs))
    process_prs("throughput", prs, date)
