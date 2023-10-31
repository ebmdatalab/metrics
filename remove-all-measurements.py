from metrics import influxdb
from metrics.logs import setup_logging


setup_logging()

measurements = [
    "github_pull_requests_queue",
    "github_pull_requests_queue_older_than_2_days",
    "github_pull_requests_queue_older_than_10_days",
    "github_pull_requests_queue_older_than_30_days",
    "github_pull_requests_queue_older_than_60_days",
    "github_pull_requests_throughput",
]

for measurement in measurements:
    influxdb.delete(measurement)
