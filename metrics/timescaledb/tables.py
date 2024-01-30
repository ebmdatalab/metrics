from sqlalchemy import TIMESTAMP, Column, Integer, MetaData, Table, Text


metadata = MetaData()

GitHubPullRequests = Table(
    "github_pull_requests",
    metadata,
    Column("time", TIMESTAMP(timezone=True), primary_key=True),
    Column("name", Text, primary_key=True),
    Column("value", Integer),
    Column("author", Text, primary_key=True),
    Column("organisation", Text),
    Column("repo", Text, primary_key=True),
)


GitHubVulnerabilities = Table(
    "github_vulnerabilities",
    metadata,
    Column("time", TIMESTAMP(timezone=True), primary_key=True),
    Column("value", Integer),
    Column("open", Integer),
    Column("closed", Integer),
    Column("organisation", Text),
    Column("repo", Text, primary_key=True),
)


SlackTechSupport = Table(
    "slack_tech_support",
    metadata,
    Column("time", TIMESTAMP(timezone=True), primary_key=True),
    Column("name", Text, primary_key=True),
    Column("value", Integer),
)

GenericCounter = Table(
    "generic_counter",
    metadata,
    Column("id", Text, primary_key=True),
    Column("time", TIMESTAMP(timezone=True), primary_key=True),
    Column("name", Text),
    Column("value", Integer),
)
