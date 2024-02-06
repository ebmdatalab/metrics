import argparse
import datetime
import os

import pandas as pd
from github import Github
from tqdm import tqdm

from metrics.github.client import GitHubClient
from metrics.github.issue_reactions import fetch_reactions


def calculate_time_per_step(data):
    """
    Takes in a DataFrame of reactions and calculates the time spent between each step.
    """
    data["created_at"] = pd.to_datetime(data["created_at"])

    time_diffs = []

    for (issue, user), group in data.groupby(["issue", "user"]):
        group = group.sort_values(by=["created_at"])
        for i in range(1, len(group)):
            time_diff = (
                group.iloc[i]["created_at"] - group.iloc[i - 1]["created_at"]
            ).total_seconds()
            time_diffs.append(
                {
                    "issue": issue,
                    "user": user,
                    "from_reaction": group.iloc[i - 1]["type"],
                    "to_reaction": group.iloc[i]["type"],
                    "time_diff_sec": time_diff,
                }
            )

    return pd.DataFrame(time_diffs)


def extract_issue_reactions(repo, token, since=None, closed_only=True):
    """
    Extracts reactions data from a GitHub repo and saves it as a csv file.

    Args:
        repo (str): GitHub repo to extract issues from. e.g 'ebmdatalab/opensafely-output-review'
        token (str): GitHub PAT
        since (str): Start of time period to extract issue from. Format - 'YYYY-MM-DD'. Defaults to all issues.
    Returns:
        df (pd.DataFrame): DataFrame containing issue data. One row per issue.
    """
    g = Github(token)
    r = g.get_repo(repo)

    if closed_only:
        state = "closed"
    else:
        state = "all"

    issues_dict = {}

    if since:
        start = datetime.datetime.strptime(since, "%Y-%m-%d")
        issues = r.get_issues(state=state, since=start)
    else:
        issues = r.get_issues(state=state)

    reactions_dfs = []

    for issue in tqdm(issues):
        num = issue.number

        reactions = {"issue": [], "user": [], "type": [], "created_at": []}
        for r in issue.get_reactions():
            reaction = r.content
            user = r.user.login

            reactions["user"].append(user)
            reactions["type"].append(reaction)
            reactions["created_at"].append(r.created_at)
            reactions["issue"].append(num)

        reactions_df = pd.DataFrame(reactions)
        reactions_df["created_at"] = pd.to_datetime(reactions_df["created_at"])

        reactions_dfs.append(reactions_df)

    if since:
        filename = f"data/time_by_step_{repo.replace('/', '-')}_{since}.csv"
    else:
        filename = f"data/time_by_step_{repo.replace('/', '-')}.csv"

    reactions_df = pd.concat(reactions_dfs)
    reactions_df = reactions_df.sort_values(by=["issue", "user", "created_at"])
    time_by_step = calculate_time_per_step(reactions_df)
    print(time_by_step.head())
    print(filename)
    time_by_step.to_csv(filename, index=False)


def parse_args():
    parser = argparse.ArgumentParser()

    # parser.add_argument(
    #     "--repo",
    #     required=True,
    #     type=str,
    #     help="Repo to extract issues from. e.g 'ebmdatalab/opensafely-output-review'",
    # )
    parser.add_argument(
        "--token",
        required=True,
        type=str,
        help="GitHub PAT",
    )
    parser.add_argument(
        "--since",
        default=None,
        type=str,
        help="Start of time period to extract issue from. Format - 'YYYY-MM-DD'. Defaults to all issues.",
    )

    return parser.parse_args()


def main():
    args = parse_args()
    # repo = args.repo
    token = args.token
    start_time = args.since

    # extract_issue_reactions(repo, token, start_time)

    # use GraphQL to mirror what the data pulling that was being done with pyGithub

    # use our client to get free pagination
    ebmdatalab_token = os.environ["GITHUB_EBMDATALAB_TOKEN"]
    client = GitHubClient("ebmdatalab", ebmdatalab_token)

    reactions = fetch_reactions(client)
    print(len(list(reactions)))


if __name__ == "__main__":
    main()
