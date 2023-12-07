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

## Running
Start the local docker stack with:
```
just grafana
```

This will spin up Grafana, it's own database, and a TimescaleDB instance.
You can then run the metrics CLI with:
```
just metrics
```

## Tests
Run the tests with:
```
just test <args>
```
