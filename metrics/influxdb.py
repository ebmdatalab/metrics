import os
from datetime import UTC, datetime, time

import influxdb_client
import structlog
from influxdb_client import Point
from influxdb_client.client.write_api import WriteOptions, WriteType


log = structlog.get_logger()

TOKEN = os.environ["INFLUXDB_TOKEN"]
BUCKET = "data"
ORG = "bennett"
URL = "http://localhost:8086"

client = influxdb_client.InfluxDBClient(url=URL, token=TOKEN, org=ORG)
delete_api = client.delete_api()
# write_api = client.write_api(write_options=SYNCHRONOUS)
write_api = client.write_api(
    write_options=WriteOptions(
        write_type=WriteType.synchronous,
        batch_size=1000,
    )
)


def delete(key):
    measurement = f"_measurement={key}"
    log.info("Removing %s", key)

    start = "1970-01-01T00:00:00Z"
    stop = datetime.now(tz=UTC).isoformat(timespec="seconds")

    delete_api.delete(start, stop, measurement, bucket=BUCKET, org=ORG)


def write(measurement, date, value, tags=None):
    # convert date to a timestamp
    # TODO: do we need to do any checking to make sure this is tz-aware and in
    # UTC?
    dt = datetime.combine(date, time())

    point = Point(measurement).field("number", value).time(dt)

    if tags is not None:
        for k, v in tags.items():
            point = point.tag(k, v)

    write_api.write(bucket=BUCKET, org=ORG, record=point)

    log.debug(
        measurement,
        date=dt.isoformat(),
        number=value,
        **tags,
    )


if __name__ == "__main__":
    print(datetime.now())
    point = Point("github.pull_requests").field("testing", 79).time(datetime.now())
    write_api.write(bucket=BUCKET, org=ORG, record=point)
