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
                breakpoint()
                print(len(orgs))

            org = list(orgs)[0]

            writer.write(
                date,
                len(prs_by_author_and_repo),
                name=name,
                author=author,
                organisation=org,
                repo=repo,
            )
