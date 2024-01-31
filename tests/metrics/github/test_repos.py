from metrics.github.repos import tech_owned_repo


def test_dont_filter_out_repos_from_unknown_orgs():
    assert tech_owned_repo({"name": "any", "org": "other"})


def test_filtering_of_tech_owned_repos():
    assert tech_owned_repo({"name": "metrics", "org": "ebmdatalab"})
    assert not tech_owned_repo(
        {"name": "clinicaltrials-act-tracker", "org": "ebmdatalab"}
    )
