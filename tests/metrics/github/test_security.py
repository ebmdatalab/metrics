import datetime

from metrics.github import security
from metrics.github.github import Repo


def test_vulnerability_open_on():
    v = security.Vulnerability(datetime.date(2023, 10, 26), None, None, None)

    assert v.is_open_on(datetime.date(2023, 10, 29))


def test_vulnerability_open_on_same_day():
    v = security.Vulnerability(datetime.date(2023, 10, 26), None, None, None)

    assert v.is_open_on(datetime.date(2023, 10, 26))


def test_vulnerability_open_on_date_in_past():
    v = security.Vulnerability(datetime.date(2023, 10, 26), None, None, None)

    assert not v.is_open_on(datetime.date(2023, 10, 20))


def test_vulnerability_open_has_been_closed():
    v = security.Vulnerability(
        datetime.date(2023, 10, 26), datetime.date(2023, 10, 28), None, None
    )

    assert not v.is_open_on(datetime.date(2023, 10, 30))


def test_vulnerability_fixed_on_is_closed():
    v = security.Vulnerability(
        datetime.date(2023, 10, 26), datetime.date(2023, 10, 28), None, None
    )

    assert v.is_closed_on(datetime.date(2023, 10, 29))


def test_vulnerability_fixed_on_still_open():
    v = security.Vulnerability(
        datetime.date(2023, 10, 26), datetime.date(2023, 10, 28), None, None
    )

    assert not v.is_closed_on(datetime.date(2023, 10, 27))


def test_vulnerability_dismissed_on_is_closed():
    v = security.Vulnerability(
        datetime.date(2023, 10, 26), None, datetime.date(2023, 10, 28), None
    )

    assert v.is_closed_on(datetime.date(2023, 10, 29))


def test_vulnerability_auto_dismssed_on_is_closed():
    v = security.Vulnerability(
        datetime.date(2023, 10, 26), None, None, datetime.date(2023, 10, 28)
    )

    assert v.is_closed_on(datetime.date(2023, 10, 29))


def test_vulnerabilities(monkeypatch):
    def fake_repos():
        return [
            Repo(
                "test-org", "test", "a-team", datetime.date(2023, 10, 13), False, True
            ),
            Repo(
                "test-org", "test2", "a-team", datetime.date(2023, 10, 13), False, True
            ),
        ]

    monkeypatch.setattr(security.github, "tech_repos", fake_repos)

    def fake_vulnerabilities(org, repo):
        return [
            dict(
                createdAt="2023-10-13T00:00:00Z",
                fixedAt="2023-10-20T00:00:00Z",
                dismissedAt=None,
                autoDismissedAt=None,
            ),
            dict(
                createdAt="2023-10-13T00:00:00Z",
                fixedAt=None,
                dismissedAt="2023-10-21T00:00:00Z",
                autoDismissedAt=None,
            ),
            dict(
                createdAt="2023-10-13T00:00:00Z",
                fixedAt=None,
                dismissedAt=None,
                autoDismissedAt="2023-10-22T00:00:00Z",
            ),
            dict(
                createdAt="2023-10-26T00:00:00Z",
                fixedAt=None,
                dismissedAt=None,
                autoDismissedAt=None,
            ),
            dict(
                createdAt="2023-10-29T00:00:00Z",
                fixedAt=None,
                dismissedAt=None,
                autoDismissedAt=None,
            ),
        ]

    monkeypatch.setattr(security.query, "vulnerabilities", fake_vulnerabilities)

    result = security.vulnerabilities(datetime.date(2023, 10, 29))

    assert len(result) == 34
    assert result[0] == {
        "time": datetime.date(2023, 10, 13),
        "value": 0,
        "closed": 0,
        "open": 3,
        "organisation": "test-org",
        "repo": "test",
        "has_alerts_enabled": True,
    }
    assert result[7] == {
        "time": datetime.date(2023, 10, 20),
        "value": 0,
        "closed": 1,
        "open": 2,
        "organisation": "test-org",
        "repo": "test",
        "has_alerts_enabled": True,
    }
    assert result[33] == {
        "time": datetime.date(2023, 10, 29),
        "value": 0,
        "closed": 3,
        "open": 2,
        "organisation": "test-org",
        "repo": "test2",
        "has_alerts_enabled": True,
    }
