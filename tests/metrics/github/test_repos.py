from metrics.github.query import Repo


def test_dont_filter_out_repos_from_unknown_orgs():
    assert make_repo(org="other", name="any").is_tech_owned()


def test_filtering_of_tech_owned_repos():
    assert make_repo(org="ebmdatalab", name="metrics").is_tech_owned()
    assert not make_repo(
        org="ebmdatalab", name="clinicaltrials-act-tracker"
    ).is_tech_owned()


def make_repo(org, name):
    return Repo(
        org=org, name=name, archived_on=None, has_vulnerability_alerts_enabled=False
    )
