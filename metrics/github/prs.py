from datetime import datetime, time


def drop_archived_prs(prs, date):
    """
    Drop PRs where their repo's archival date happened before the given date

    We expose a repo's archived date in both date and datetime format, so this
    function will pick the relevant one based on the type of the given date.
    """

    def keep(pr, date):
        if not pr["repo_archived_at"]:
            # the repo hasn't been archived yet
            return True

        if date < pr["repo_archived_at"].date():
            # the repo has not been archived by date
            return True

        return False

    return [pr for pr in prs if keep(pr, date)]


def iter_prs(prs, date, name):
    """
    Given a list of PRs, break them down in series for writing

    We're storing counts of PRs for a given date based on (repo, author).  This
    function does the breaking down and counting.
    """
    repos = {pr["repo"] for pr in prs}
    for repo in repos:
        authors = {pr["author"] for pr in prs if pr["repo"] == repo}
        for author in authors:
            prs_by_author_and_repo = [
                pr for pr in prs if pr["repo"] == repo and pr["author"] == author
            ]

            orgs = {pr["org"] for pr in prs_by_author_and_repo}
            if len(orgs) > 1:
                # we expected the given PRs to be from the same org
                raise ValueError(
                    f"Expected 1 org, but found {len(orgs)} orgs, unsure how to proceed"
                )

            org = list(orgs)[0]

            yield {
                "time": datetime.combine(date, time()),
                "value": len(prs_by_author_and_repo),
                "name": name,
                "author": author,
                "organisation": org,
                "repo": repo,
            }
