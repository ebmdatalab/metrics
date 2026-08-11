# Load .env files by default
set dotenv-load := true
set positional-arguments := true

export DEV_USERID := `id -u`
export DEV_GROUPID := `id -g`


# list available commands
default:
    @"{{ just_executable() }}" --list

# Create a valid .env if none exists
_dotenv:
    #!/usr/bin/env bash
    set -euo pipefail

    if [[ ! -f .env ]]; then
      echo "No '.env' file found; creating a default '.env' from 'dotenv-sample'"
      cp dotenv-sample .env
    fi

# Check if a .env exists
# Use this (rather than _dotenv or devenv) for recipes that require that a .env file exists.
# just will not pick up environment variables from a .env that it's just created,
# and there isn't an easy way to load those into the environment, so we just
# prompt the user to run just devenv to set up their local environment properly.
_checkenv:
    #!/usr/bin/env bash
    set -euo pipefail

    if [[ ! -f .env ]]; then
        echo "No '.env' file found; run 'just devenv' to create one"
        exit 1
    fi

# clean up temporary files
clean:
    rm -rf .venv

# Install production requirements into and remove extraneous packages from venv
prodenv:
    uv sync --no-dev

# Install dev requirements into venv without removing extraneous packages
devenv: _dotenv && install-precommit
    uv sync --inexact

# Ensure precommit is installed
install-precommit:
    #!/usr/bin/env bash
    set -euo pipefail

    BASE_DIR=$(git rev-parse --show-toplevel)
    test -f $BASE_DIR/.git/hooks/pre-commit || uv run pre-commit install

# Upgrade a single package
upgrade-package package: && uvmirror devenv
    uv lock --upgrade-package {{ package }}

# Upgrade all packages to the latest versions (with cooldown)
upgrade-all cooldown="7 days ago": && uvmirror devenv
    uv lock --upgrade --exclude-newer "{{ cooldown }}"

# update the uv mirror requirements file
uvmirror file="requirements.uvmirror":
    rm -f {{ file }}
    uv export --format requirements-txt --frozen --no-hashes --all-groups --all-extras > {{ file }}

# This is the default input command to update-dependencies action
# https://github.com/bennettoxford/update-dependencies-action
update-dependencies: upgrade-all

# *args is variadic, 0 or more. This allows us to do `just test -k match`, for example.

# Run the tests
test *args:
    uv run coverage run --module pytest "$@"
    uv run coverage report || uv run coverage html

format *args:
    uv run ruff format --diff --quiet "$@"

lint *args:
    uv run ruff check "$@" .

lint-actions:
    docker run --rm -v $(pwd):/repo:ro --workdir /repo rhysd/actionlint:1.7.8@sha256:96d4a8c87dbbfb3bdd324f8fdc285fc3df5261e2decc619a4dd7e8ee52bbfd46 -color

# Run the various dev checks but does not change any files
check:
    #!/usr/bin/env bash
    set -euo pipefail

    failed=0

    check() {
      echo -e "\e[1m=> ${1}\e[0m"
      rc=0
      # Run it
      eval $1 || rc=$?
      # Increment the counter on failure
      if [[ $rc != 0 ]]; then
        failed=$((failed + 1))
        # Add spacing to separate the error output from the next check
        echo -e "\n"
      fi
    }

    check "just check-lockfile"
    check "just format"
    check "just lint"
    test -d docker/ && check "just docker/lint"

    if [[ $failed > 0 ]]; then
      echo -en "\e[1;31m"
      echo "   $failed checks failed"
      echo -e "\e[0m"
      exit 1
    fi

# validate uv.lock
check-lockfile:
    uv lock --check

# Fix formatting, import sort ordering, and justfile
fix:
    -uv run ruff check --fix .
    -uv run ruff format .
    -just --fmt --unstable

# Run the grafana stack
grafana:
    docker compose up grafana

# Run a metrics task (defaults to running all tasks)
metrics *args: devenv
    #!/usr/bin/env bash
    set -euo pipefail

    MODULE="metrics.tasks{{ if args == "" { "" } else { "." + args } }}"
    uv run python -m $MODULE

docker-build env="dev": _dotenv
    #!/usr/bin/env bash
    set -euo pipefail

    test -z "${SKIP_BUILD:-}" || { echo "SKIP_BUILD set"; exit 0; }

    # set build args for prod builds
    export BUILD_DATE=$(date -u +'%y-%m-%dT%H:%M:%SZ')
    export GITREF=$(git rev-parse --short HEAD)

    # build the thing
    docker compose build --pull metrics-{{ env }}


# run command in dev|prod container
docker-run env="dev" *args="": _dotenv
    {{ just_executable() }} docker-build {{ env }}
    docker compose run --rm metrics-{{ env }} {{ args }}

# See DEVELOPERS.md
clean-cache:
    rm -f github-cache.sqlite
