import datetime
from datetime import date

from metrics.github import security
from metrics.github.query import Repo


def fake_repos(client, org):
    return [
        Repo(
            org,
            "opencodelists",
            created_on=date.min,
            archived_on=None,
            has_vulnerability_alerts_enabled=True,
        ),
        Repo(
            org,
            "old-repo",
            created_on=date.min,
            archived_on=datetime.date.fromisoformat("2023-04-20"),
            has_vulnerability_alerts_enabled=False,
        ),
        Repo(
            org,
            "job-server",
            created_on=date.min,
            archived_on=None,
            has_vulnerability_alerts_enabled=True,
        ),
    ]


def fake_vulnerabilities(client, repo):
    response = [
        {
            "createdAt": "2022-02-10T01:36:54Z",
            "fixedAt": None,
            "dismissedAt": None,
        },
        {
            "createdAt": "2022-10-18T17:20:30Z",
            "fixedAt": "2022-10-24T14:27:29Z",
            "dismissedAt": None,
        },
        {
            "createdAt": "2022-10-18T21:08:22Z",
            "fixedAt": "2022-11-09T13:01:04Z",
            "dismissedAt": None,
        },
        {
            "createdAt": "2022-11-01T17:52:53Z",
            "fixedAt": "2022-11-07T15:14:37Z",
            "dismissedAt": None,
        },
        {
            "createdAt": "2023-08-30T04:44:56Z",
            "fixedAt": None,
            "dismissedAt": "2023-09-04T15:07:44Z",
        },
        {
            "createdAt": "2023-10-03T02:46:00Z",
            "fixedAt": None,
            "dismissedAt": None,
        },
        {
            "createdAt": "2023-10-26T15:02:17Z",
            "fixedAt": None,
            "dismissedAt": None,
        },
    ]
    return response


def test_get_repos(monkeypatch):
    monkeypatch.setattr(security.query, "repos", fake_repos)
    monkeypatch.setattr(security.query, "vulnerabilities", fake_vulnerabilities)
    fake_client = lambda: None  # pragma: no cover

    result = list(security.get_repos(fake_client, "test-org"))

    assert len(result) == 2
    assert result[0].name == "opencodelists"
    assert len(result[0].vulnerabilities) == 7
    assert result[1].name == "job-server"
    assert len(result[1].vulnerabilities) == 7


def test_get_repos_when_no_vulnerabilities_returns_all_nonarchived_repos(monkeypatch):
    monkeypatch.setattr(security.query, "repos", fake_repos)
    monkeypatch.setattr(security.query, "vulnerabilities", lambda x, y: [])
    fake_client = lambda: None  # pragma: no cover

    result = list(security.get_repos(fake_client, "test-org"))

    assert len(result) == 2


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
    def fake_repos(client, org):
        vulnerabilities = [
            security.Vulnerability(date(2023, 10, 13), date(2023, 10, 20), None),
            security.Vulnerability(date(2023, 10, 13), None, date(2023, 10, 21)),
            security.Vulnerability(date(2023, 10, 26), None, None),
            security.Vulnerability(date(2023, 10, 29), None, None),
        ]
        return [
            security.Repo("test", org, date(2023, 10, 13), True, vulnerabilities),
            security.Repo("test2", org, date(2023, 10, 13), True, vulnerabilities),
        ]

    monkeypatch.setattr(security, "get_repos", fake_repos)

    result = security.vulnerabilities({}, "test-org", date(2023, 10, 29))

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
