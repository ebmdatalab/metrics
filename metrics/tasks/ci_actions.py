import os
import sys
from datetime import UTC, datetime

import structlog

from metrics import timescaledb
from metrics.github.client import GitHubRestClient


log = structlog.get_logger()


def main():  # pragma: no cover
    os_token = os.environ["GITHUB_OS_TOKEN"]

    client = GitHubRestClient("opensafely", os_token)

    rows = []
    exclude_repos = ["documentation", "research-template"]
    for repo_page in client.get_paged_results("/orgs/opensafely/repos"):
        for repo_name in [repo["name"] for repo in repo_page]:
            if repo_name in exclude_repos:
                continue
            log.info("Getting data for repo: %s", repo_name)
            for page in client.get_paged_results(
                f"/repos/opensafely/{repo_name}/actions/runs"
            ):
                # Extracting information
                run_info = [
                    (
                        run["id"],
                        run["created_at"],
                        run["conclusion"] if run["conclusion"] else "Pending or Failed",
                    )
                    for run in page["workflow_runs"]
                ]

                # Output
                for pk, run_date, status in run_info:
                    if status == "success":
                        status_code = 0
                    else:
                        status_code = 1

                    name = f"ci_tests.opensafely.{repo_name}.status_code"

                    date_format = "%Y-%m-%dT%H:%M:%SZ"
                    # Set the timezone to UTC

                    parsed_datetime = datetime.strptime(run_date, date_format).replace(
                        tzinfo=UTC
                    )
                    rows.append(
                        {
                            "id": pk,
                            "time": parsed_datetime,
                            "name": name,
                            "value": status_code,
                        }
                    )
    timescaledb.reset_table(timescaledb.GenericCounter)
    timescaledb.write(timescaledb.GenericCounter, rows)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
