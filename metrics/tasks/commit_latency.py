import csv
import datetime
import itertools
import sys
from dataclasses import dataclass

import altair
import git
import pandas

from metrics.github import query


@dataclass(frozen=True)
class Commit:
    sha: str
    authored: datetime.datetime
    released: datetime.datetime

    def latency(self):
        return (self.released - self.authored) / datetime.timedelta(days=1)


def main():
    # grab_workflow_runs()
    releases = load_releases()
    commits = assemble_commits(releases)
    data = shape_data(commits)
    draw_chart(data)


def load_releases():
    releases = set()
    with open('workflow-runs.csv', newline='') as f:
        for datetime_str, sha in csv.reader(f):
            datetime_ = datetime.datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M:%SZ').replace(
                tzinfo=datetime.timezone.utc)
            releases.add((datetime_, sha))
    return releases


def assemble_commits(releases):
    commits = list()
    repo = git.Repo("~/src/opensafely-core/job-server")
    for previous_release, this_release in itertools.pairwise(sorted(releases, key=lambda r: r[0])):
        _, prev_sha = previous_release
        this_datetime, this_sha = this_release
        for commit in reversed(list(repo.iter_commits(rev=f"{prev_sha}...{this_sha}"))):
            if commit.message.startswith("Merge pull request "):
                continue
            commits.append(Commit(commit.hexsha, commit.authored_datetime, this_datetime))
    return commits


def shape_data(commits):
    groups = pandas.DataFrame.from_records([
            {"released": commit.released, "latency": commit.latency()}
            for commit in commits
        ]).groupby(pandas.Grouper(key="released", freq="1ME"))

    deciles = range(10, 100, 10)
    deciles_data = [groups.quantile(decile/100.0).rename(columns={"latency": f"p{decile}"}) for decile in deciles]

    percentiles = list(range(1, 10, 1)) + list(range(91, 100, 1))
    percentile_data = [groups.quantile(percentile/100.0).rename(columns={"latency": f"p{percentile}"}) for percentile in percentiles]

    return pandas.concat(deciles_data + percentile_data, axis=1) \
        .reset_index() \
        .melt(id_vars=["released"], value_vars=[f"p{decile}" for decile in deciles] + [f"p{percentile}" for percentile in percentiles], var_name="quantile", value_name="latency")


def draw_chart(data):
    altair.Chart(data, title="Latency between authoring and release for Job Server commits (monthly deciles)") \
        .mark_line() \
        .encode(
            x=altair.X("released", title="Release date"),
            y=altair.Y("latency", title="Latency (days)").scale(type="log"),
            detail="quantile",
            strokeDash=altair.condition(
                "datum.quantile == 'p50'",
                altair.value([1, 0]),
                altair.value([2, 5])
            ),
            strokeOpacity=altair.condition(
                altair.FieldOneOfPredicate("quantile", ["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8", "p9", "p99", "p98", "p97", "p96", "p95", "p94", "p93", "p92", "p91"]),
                altair.value(0.3),
                altair.value(1.0),
            )
        ) \
        .save("scatterplot.html")


def grab_workflow_runs():
    runs = query.workflow_runs("opensafely-core", "job-server")
    for run in runs:
        if not run["name"] == "CI":
            continue
        print(f"{run["created_at"]},{run["head_sha"]}")


if __name__ == "__main__":
    sys.exit(main())
