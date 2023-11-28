from datetime import date

from metrics.github import security


def fake_vulnerabilities(org):
    github_response = [
        {
            "name": "opencodelists",
            "vulnerabilityAlerts": {
                "nodes": [
                    {
                        "number": 8,
                        "createdAt": "2022-02-10T01:36:54Z",
                        "fixedAt": None,
                        "dismissedAt": None,
                    },
                    {
                        "number": 23,
                        "createdAt": "2022-10-18T17:20:30Z",
                        "fixedAt": "2022-10-24T14:27:29Z",
                        "dismissedAt": None,
                    },
                    {
                        "number": 24,
                        "createdAt": "2022-10-18T21:08:22Z",
                        "fixedAt": "2022-11-09T13:01:04Z",
                        "dismissedAt": None,
                    },
                    {
                        "number": 25,
                        "createdAt": "2022-11-01T17:52:53Z",
                        "fixedAt": "2022-11-07T15:14:37Z",
                        "dismissedAt": None,
                    },
                    {
                        "number": 55,
                        "createdAt": "2023-08-30T04:44:56Z",
                        "fixedAt": None,
                        "dismissedAt": "2023-09-04T15:07:44Z",
                    },
                    {
                        "number": 57,
                        "createdAt": "2023-10-03T02:46:00Z",
                        "fixedAt": None,
                        "dismissedAt": None,
                    },
                    {
                        "number": 64,
                        "createdAt": "2023-10-26T15:02:17Z",
                        "fixedAt": None,
                        "dismissedAt": None,
                    },
                ]
            },
        }
    ]
    return github_response


def test_security_number_of_alerts_today():
    today = date(2023, 11, 28)

    alerts = fake_vulnerabilities("test-org")[0]["vulnerabilityAlerts"]["nodes"]
    result = security.parse_vulnerabilities_for_date(
        alerts, "opencodelists", today, "test-org"
    )

    assert str(result["date"]) == "2023-11-28"
    assert result["closed"] == 4
    assert result["open"] == 3


def test_security_number_of_alerts_last_year():
    target_date = date(2022, 11, 1)

    alerts = fake_vulnerabilities("test-org")[0]["vulnerabilityAlerts"]["nodes"]
    result = security.parse_vulnerabilities_for_date(
        alerts, "opencodelists", target_date, "test-org"
    )

    assert str(result["date"]) == "2022-11-01"
    assert result["closed"] == 1
    assert result["open"] == 3


def test_security_parse_vulnerabilities_earliest_and_latest_date():
    result = security.parse_vulnerabilities(
        fake_vulnerabilities("test-org"), "test-org"
    )

    assert len(result) == 624
    assert str(result[0]["date"]) == "2022-02-10"
    assert result[0]["closed"] == 0
    assert result[0]["open"] == 1
    assert str(result[-1]["date"]) == "2023-10-26"
    assert result[-1]["closed"] == 4
    assert result[-1]["open"] == 3
