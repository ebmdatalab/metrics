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


## Tests
Run the tests with:
```
just test <args>
```
