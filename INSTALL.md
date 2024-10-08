# Metrics deployment instructions
## Create app
```bash
dokku$ dokku apps:create metrics
dokku$ dokku git:set metrics deploy-branch main
```

## Configure app
```bash
dokku config:set metrics GITHUB_EBMDATALAB_TOKEN='xxx'
dokku config:set metrics GITHUB_OS_CORE_TOKEN='xxx'
dokku config:set metrics GITHUB_OS_TOKEN='xxx'
dokku config:set metrics SLACK_SIGNING_SECRET='xxx'
dokku config:set metrics SLACK_TECH_SUPPORT_CHANNEL_ID='xxx'
dokku config:set metrics SLACK_TOKEN='xxx'
dokku config:set metrics TIMESCALEDB_URL='xxx'
dokku config:set metrics SENTRY_DSN='xxx'
```

The `GITHUB_EBMDATALAB_TOKEN` and `GITHUB_OS_CORE_TOKEN` are fine-grained GitHub personal access tokens that are used for authenticating with the GitHub GraphQL API.
Each token is assigned to a single organisation and should have the following *read-only* permissions:

* organisation permissions: members
* *all repositories* owned by the organisation with the following permissions:
Code scanning alerts, Dependabot alerts, Issues, Metadata, Pull requests and Repository security advisories

The `GITHUB_OS_TOKEN` is a fine-grained GitHub personal access token that is used for authenticating with the GitHub REST API.
It is assigned to a single organisation and should have the following *read-only* permissions:
* organisation permissions: organisation codespaces
* *all repositories* owned by the organisation with the following permissions:
Codespaces and Metadata

## Disable checks
Dokku performs health checks on apps during deploy by sending requests to port 80.
This tool isn't a web app so it can't accept requests on a port.
Disable the checks so deploys can happen.
```bash
dokku$ dokku checks:disable metrics
```

## Set up storage
This is only needed for backfills which make use of a SQLite db cache.
```bash
# the metrics container runs as uid 1000 (metrics) internally, which corresponds to a dev user on the dokku3 host.
# the other dokku containers on dokku3 run as uid 1013 (dokku), which corresponds correctly to the dokku user on the dokku3 host.
# let's tell the container to run as 1013, then we can use the same file permissions
dokku$ dokku docker-options:add grafana deploy "--user 1013"
dokku$ dokku docker-options:add grafana run "--user 1013"

dokku$ dokku storage:ensure-directory metrics
dokku$ sudo chown -R dokku:dokku /var/lib/dokku/data/storage/metrics/
dokku$ dokku storage:mount metrics /var/lib/dokku/data/storage/metrics/:/storage
```

## Ensure persistent logs
```bash
dokku$ sudo mkdir -p /var/log/journal
```
