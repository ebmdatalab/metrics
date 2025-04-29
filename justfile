# Load .env files by default
set dotenv-load := true

export VIRTUAL_ENV  := env_var_or_default("VIRTUAL_ENV", ".venv")

export BIN := VIRTUAL_ENV + if os_family() == "unix" { "/bin" } else { "/Scripts" }
export PIP := BIN + if os_family() == "unix" { "/python -m pip" } else { "/python.exe -m pip" }

export DEFAULT_PYTHON := if os_family() == "unix" { "python3.12" } else { "python" }

export DEV_USERID := `id -u`
export DEV_GROUPID := `id -g`


# list available commands
default:
    @"{{ just_executable() }}" --list


# clean up temporary files
clean:
    rm -rf .venv


_env:
    #!/usr/bin/env bash
    set -euo pipefail

    test -f .env || cp dotenv-sample .env


# ensure valid virtualenv
virtualenv: _env
    #!/usr/bin/env bash
    set -euo pipefail

    # allow users to specify python version in .env
    PYTHON_VERSION=${PYTHON_VERSION:-$DEFAULT_PYTHON}

    # create venv and upgrade pip
    test -d $VIRTUAL_ENV || { $PYTHON_VERSION -m venv $VIRTUAL_ENV && $PIP install pip==25.0.1; }

    # ensure we have pip-tools so we can run pip-compile
    test -e $BIN/pip-compile || $PIP install pip-tools


_compile src dst *args: virtualenv
    #!/usr/bin/env bash
    set -euo pipefail

    # exit if src file is older than dst file (-nt = 'newer than', but we negate with || to avoid error exit code)
    test "${FORCE:-}" = "true" -o {{ src }} -nt {{ dst }} || exit 0
    $BIN/pip-compile --allow-unsafe --generate-hashes --output-file={{ dst }} {{ src }} {{ args }}


# update requirements.prod.txt if requirements.prod.in has changed
requirements-prod *args:
    "{{ just_executable() }}" _compile requirements.prod.in requirements.prod.txt {{ args }}


# update requirements.dev.txt if requirements.dev.in has changed
requirements-dev *args: requirements-prod
    "{{ just_executable() }}" _compile requirements.dev.in requirements.dev.txt {{ args }}


# ensure prod requirements installed and up to date
prodenv: requirements-prod
    #!/usr/bin/env bash
    set -euo pipefail

    # exit if .txt file has not changed since we installed them (-nt == "newer than', but we negate with || to avoid error exit code)
    test requirements.prod.txt -nt $VIRTUAL_ENV/.prod || exit 0

    $PIP install -r requirements.prod.txt
    touch $VIRTUAL_ENV/.prod


# && dependencies are run after the recipe has run. Needs just>=0.9.9. This is
# a killer feature over Makefiles.
#
# ensure dev requirements installed and up to date
devenv: prodenv requirements-dev && install-precommit
    #!/usr/bin/env bash
    set -euo pipefail

    # exit if .txt file has not changed since we installed them (-nt == "newer than', but we negate with || to avoid error exit code)
    test requirements.dev.txt -nt $VIRTUAL_ENV/.dev || exit 0

    $PIP install -r requirements.dev.txt
    touch $VIRTUAL_ENV/.dev


# ensure precommit is installed
install-precommit:
    #!/usr/bin/env bash
    set -euo pipefail

    BASE_DIR=$(git rev-parse --show-toplevel)
    test -f $BASE_DIR/.git/hooks/pre-commit || $BIN/pre-commit install


# upgrade dev or prod dependencies (specify package to upgrade single package, all by default)
upgrade env package="": virtualenv
    #!/usr/bin/env bash
    set -euo pipefail

    opts="--upgrade"
    test -z "{{ package }}" || opts="--upgrade-package {{ package }}"
    FORCE=true "{{ just_executable() }}" requirements-{{ env }} $opts


update-dependencies: virtualenv
    just upgrade prod
    just upgrade dev


# *args is variadic, 0 or more. This allows us to do `just test -k match`, for example.
# Run the tests
test *args: devenv
    $BIN/pytest {{ args }}


coverage: devenv
    $BIN/coverage run --module pytest
    $BIN/coverage report || $BIN/coverage html


black *args=".": devenv
    $BIN/black --check {{ args }}

ruff *args=".": devenv
    $BIN/ruff check {{ args }}

# run the various dev checks but does not change any files
check: black ruff


# fix formatting and import sort ordering
fix: devenv
    $BIN/black .
    $BIN/ruff check --fix .


# Run the grafana stack
grafana:
    docker compose up grafana


# Run a metrics task (defaults to running all tasks)
metrics *args: devenv
    #!/usr/bin/env bash
    set -euo pipefail

    MODULE="metrics.tasks{{ if args == "" { "" } else { "." + args } }}"
    $BIN/python -m $MODULE


docker-build env="dev": _env
    #!/usr/bin/env bash
    set -euo pipefail

    test -z "${SKIP_BUILD:-}" || { echo "SKIP_BUILD set"; exit 0; }

    # set build args for prod builds
    export BUILD_DATE=$(date -u +'%y-%m-%dT%H:%M:%SZ')
    export GITREF=$(git rev-parse --short HEAD)

    # build the thing
    docker compose build --pull metrics-{{ env }}


# run command in dev|prod container
docker-run env="dev" *args="": _env
    {{ just_executable() }} docker-build {{ env }}
    docker compose run --rm metrics-{{ env }} {{ args }}

# See DEVELOPERS.md
clean-cache:
    rm -f github-cache.sqlite
