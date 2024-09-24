# Notes for developers

## System requirements

### just

```sh
# macOS
brew install just

# Linux
# Install from https://github.com/casey/just/releases

# Add completion for your shell. E.g. for bash:
source <(just --completions bash)

# Show all available commands
just #  shortcut for just --list
```


## Local development environment

Set up a local development environment with:
```
just devenv
```

Populate the generated `.env` file with the GitHub PATs described in the [install instructions](INSTALL.md#configure-app).

## Running Grafana
Start the local docker stack with:
```
just grafana
```

This will spin up Grafana, its own database, and a TimescaleDB instance.

Grafana is available at [http://localhost:3000](http://localhost:3000).
The default credentials are `admin`/`admin`; Grafana asks you to change these when you first log in, but you can skip the change.

Add a datasource in [Grafana's settings](http://localhost:3000/connections/datasources).
Copy the details from [production](https://dashboards.opensafely.org/connections/datasources),
with the exception of the connection details which copy by copied from [docker-compose.yaml](https://github.com/ebmdatalab/metrics/blob/a543e8817898278d663c08243fa26359cdb5230e/docker-compose.yaml#L32-L42)
(the server address is the service name)

To add a dashboard:
1. Go to the [production dashboard](https://dashboards.opensafely.org/dashboards) that you want to copy.
2. Go to the "share" icon on the top row and to the "Export" tab.
3. Select "Export for sharing externally" and "Save to file".
4. Go to your local Grafana and [import](https://dashboards.opensafely.org/dashboards) the dashboard (you need to explicitly set the datasource).

## Running metrics tasks

You'll need to have timescale db running in the backend, either by running `just grafana`, or alternatively, to start TimeScaleDB without starting Grafana by doing
```
docker compose up timescaledb
```

You can then run the metrics tasks with:
```
just metrics
```

Specify an individual task by passing in the module name
```
just metrics <module_name>
```

e.g `just metrics prs` to run metrics/tasks/prs.py

All tasks are defined in `metrics/tasks` and must have a `main()` function that takes no arguments.

### Speeding up development

You can set a flag to trigger a fast mode which only retrieves and handful of PRs
but allows the main code paths to be tested quickly.

```
DEBUG_FAST=t just metrics prs
```

Alternatively you can turn on caching of GitHub API requests.
This is particularly useful when iterating on metric definitions
without changing the data that we retrieve from the API.

```
DEBUG_CACHE=t just metrics prs
```

NB that the cache has no expiry time
(although it will be bypassed on subsequent runs if `DEBUG_CACHE isn't defined).
You can clear the cache explicitly.

```
just clean-cache
```


## Tests
Run the tests with:
```
just test <args>
```

## Production

### Deployment

Changes merged to `main` are automatically deployed by GitHub actions.

### Updating metrics

Metrics that are populated by periodic tasks are automatically updated once a day by a Dokku cron job.
This process can also be triggered out-of-schedule.

```
you@your-laptop:~$ ssh dokku3.ebmdatalab.net
you@dokku3:~$ dokku cron:list metrics
ID        Schedule  Command
<the-id>  @daily    python -m metrics.tasks
you@dokku3:~$ dokku cron:run metrics <the-id>
```
