from sqlalchemy import TIMESTAMP, Boolean, Column, Integer, MetaData, Table, Text


metadata = MetaData()

GitHubPullRequests = Table(
    "github_pull_requests",
    metadata,
    Column("time", TIMESTAMP(timezone=True), primary_key=True),
    Column("name", Text, primary_key=True),
    Column("value", Integer),
    Column("author", Text, primary_key=True),
    Column("organisation", Text, primary_key=True),
    Column("repo", Text, primary_key=True),
)


GitHubVulnerabilities = Table(
    "github_vulnerabilities",
    metadata,
    Column("time", TIMESTAMP(timezone=True), primary_key=True),
    Column("value", Integer),
    Column("open", Integer),
    Column("closed", Integer),
    Column("organisation", Text, primary_key=True),
    Column("repo", Text, primary_key=True),
    Column("has_alerts_enabled", Boolean),
)


SlackTechSupport = Table(
    "slack_tech_support",
    metadata,
    Column("time", TIMESTAMP(timezone=True), primary_key=True),
    Column("name", Text, primary_key=True),
    Column("value", Integer),
)
