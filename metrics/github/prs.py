def drop_archived_prs(prs, key="created"):
    """
    Drop PRs where the given key happened before the repo's archival date

    By default this removes PRs opened after the point at which a repo was
    archived, but can be configured for other checks, eg merging.
    """

    def predicate(pr, key):
        if not pr["repo_archived_at"]:
            return True

        if pr[key] < pr["repo_archived_at"]:
            return True

        return False

    return [pr for pr in prs if predicate(pr, key)]


def process_prs(writer, prs, date, name=""):
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

            writer.write(
                date,
                len(prs_by_author_and_repo),
                name=name,
                author=author,
                organisation=org,
                repo=repo,
            )
