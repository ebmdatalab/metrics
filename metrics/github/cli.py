import os

import click
import structlog

from metrics.github.prs import fetch_prs, old_prs, pr_throughput

from .. import timescaledb
from .client import GitHubClient


log = structlog.get_logger()


@click.command()
@click.pass_context
def github(ctx):
    ctx.ensure_object(dict)

    ebmdatalab_token = os.environ["GITHUB_EBMDATALAB_TOKEN"]
    os_core_token = os.environ["GITHUB_OS_CORE_TOKEN"]

    client = GitHubClient("ebmdatalab", ebmdatalab_token)
    log.info("Working with org: %s", client.org)
    ebmdatalab_prs = list(fetch_prs(client))

    client = GitHubClient("opensafely-core", os_core_token)
    log.info("Working with org: %s", client.org)
    os_core_prs = list(fetch_prs(client))

    timescaledb.reset_table(timescaledb.GitHubPullRequests)

    timescaledb.write(
        timescaledb.GitHubPullRequests, old_prs(ebmdatalab_prs, days_threshold=7)
    )
    timescaledb.write(timescaledb.GitHubPullRequests, pr_throughput(ebmdatalab_prs))

    timescaledb.write(
        timescaledb.GitHubPullRequests, old_prs(os_core_prs, days_threshold=7)
    )
    timescaledb.write(timescaledb.GitHubPullRequests, pr_throughput(os_core_prs))
