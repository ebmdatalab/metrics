from sqlalchemy import TIMESTAMP, Boolean, Column, Integer, MetaData, Table, Text


metadata = MetaData()


GitHubRepos = Table(
    "github_repos",
    metadata,
    Column("organisation", Text, primary_key=True),
    Column("repo", Text, primary_key=True),
    Column("owner", Text),
)


GitHubPullRequests = Table(
    "github_pull_requests",
    metadata,
    Column("time", TIMESTAMP(timezone=True), primary_key=True),
    Column("name", Text, primary_key=True),
    Column("value", Integer),
    Column("author", Text, primary_key=True),
    Column("is_content", Boolean, primary_key=True),
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


GitHubIssues = Table(
    "github_issues",
    metadata,
    Column("time", TIMESTAMP(timezone=True), primary_key=True),
    Column("organisation", Text, primary_key=True),
    Column("repo", Text, primary_key=True),
    Column("author", Text, primary_key=True),
    Column("count", Integer),
)


SlackTechSupport = Table(
    "slack_tech_support",
    metadata,
    Column("time", TIMESTAMP(timezone=True), primary_key=True),
    Column("name", Text, primary_key=True),
    Column("value", Integer),
)
