github_pull_requests = """
CREATE TABLE IF NOT EXISTS github_pull_requests (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    name TEXT NOT NULL,
    value INTEGER NOT NULL,
    author TEXT NOT NULL,
    organisation TEXT NOT NULL,
    repo TEXT NOT NULL,
    CONSTRAINT github_pull_requests_must_be_different UNIQUE (time, name, author, repo)
);
"""
slack_tech_support = """
CREATE TABLE IF NOT EXISTS slack_tech_support (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    name TEXT NOT NULL,
    value INTEGER NOT NULL,
    CONSTRAINT slack_tech_support_must_be_different UNIQUE (time, name)
);
"""
