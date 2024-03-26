from datetime import date

from metrics.github import security
from metrics.github.github import Repo


def test_vulnerability_open_on():
    v = security.Vulnerability(date(2023, 10, 26), None, None)

    assert v.is_open_on(date(2023, 10, 29))


def test_vulnerability_open_on_same_day():
    v = security.Vulnerability(date(2023, 10, 26), None, None)

    assert v.is_open_on(date(2023, 10, 26))


def test_vulnerability_open_on_date_in_past():
    v = security.Vulnerability(date(2023, 10, 26), None, None)

    assert not v.is_open_on(date(2023, 10, 20))


def test_vulnerability_open_has_been_closed():
    v = security.Vulnerability(date(2023, 10, 26), date(2023, 10, 28), None)

    assert not v.is_open_on(date(2023, 10, 30))


def test_vulnerability_closed_on():
    v = security.Vulnerability(date(2023, 10, 26), date(2023, 10, 28), None)

    assert v.is_closed_on(date(2023, 10, 29))


def test_vulnerability_closed_on_still_open():
    v = security.Vulnerability(date(2023, 10, 26), date(2023, 10, 28), None)

    assert not v.is_closed_on(date(2023, 10, 27))


def test_vulnerability_closed_on_is_closed():
    v = security.Vulnerability(date(2023, 10, 26), date(2023, 10, 28), None)

    assert v.is_closed_on(date(2023, 10, 29))


def test_vulnerabilities(monkeypatch):
    def fake_repos(org):
        return [
            Repo(org, "test", "a-team", date(2023, 10, 13), False, True),
            Repo(org, "test2", "a-team", date(2023, 10, 13), False, True),
        ]

    monkeypatch.setattr(security.github, "tech_repos", fake_repos)

    def fake_vulnerabilities(repo):
        return [
            dict(
                createdAt="2023-10-13T00:00:00Z",
                fixedAt="2023-10-20T00:00:00Z",
                dismissedAt=None,
            ),
            dict(
                createdAt="2023-10-13T00:00:00Z",
                fixedAt=None,
                dismissedAt="2023-10-21T00:00:00Z",
            ),
            dict(createdAt="2023-10-26T00:00:00Z", fixedAt=None, dismissedAt=None),
            dict(createdAt="2023-10-29T00:00:00Z", fixedAt=None, dismissedAt=None),
        ]

    monkeypatch.setattr(security.query, "vulnerabilities", fake_vulnerabilities)

    result = security.vulnerabilities("test-org", date(2023, 10, 29))

    assert len(result) == 34
    assert result[0] == {
        "time": date(2023, 10, 13),
        "value": 0,
        "closed": 0,
        "open": 2,
        "organisation": "test-org",
        "repo": "test",
        "has_alerts_enabled": True,
    }
    assert result[7] == {
        "time": date(2023, 10, 20),
        "value": 0,
        "closed": 1,
        "open": 1,
        "organisation": "test-org",
        "repo": "test",
        "has_alerts_enabled": True,
    }
    assert result[33] == {
        "time": date(2023, 10, 29),
        "value": 0,
        "closed": 2,
        "open": 2,
        "organisation": "test-org",
        "repo": "test2",
        "has_alerts_enabled": True,
    }
