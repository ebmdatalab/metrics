from metrics.timescaledb import run


def create_table(name):
    run(
        f"""
        CREATE TABLE IF NOT EXISTS {name} (
            time TIMESTAMP WITH TIME ZONE NOT NULL,
            name TEXT NOT NULL,
            value INTEGER NOT NULL,
            author TEXT NOT NULL,
            organisation TEXT NOT NULL,
            repo TEXT NOT NULL
        );
        """
    )
    run("SELECT create_hypertable(%s, 'time');", (name,))
    run(f"CREATE INDEX IF NOT EXISTS idx_{name}_time ON {name} (name, time DESC);")


names = [
    "github_pull_requests_queue",
    "github_pull_requests_queue_older_than_2_days",
    "github_pull_requests_queue_older_than_10_days",
    "github_pull_requests_queue_older_than_30_days",
    "github_pull_requests_queue_older_than_60_days",
    "github_pull_requests_throughput",
]

# for name in names:
#     create_table(name)

create_table("github_pull_requests")
