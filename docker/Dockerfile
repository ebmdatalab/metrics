# syntax=docker/dockerfile:1.2
#################################################
#
# Create base image with python installed.
#
# DL3007 ignored because base-docker we specifically always want to build on
# the latest base image, by design.
#
# hadolint ignore=DL3007
FROM ghcr.io/opensafely-core/base-docker:22.04 as base-python

# we are going to use an apt cache on the host, so disable the default debian
# docker clean up that deletes that cache on every apt install
RUN rm -f /etc/apt/apt.conf.d/docker-clean

# ensure fully working base python3.12 installation using deadsnakes ppa
# see: https://gist.github.com/tiran/2dec9e03c6f901814f6d1e8dad09528e
# use space efficient utility from base image
RUN --mount=type=cache,target=/var/cache/apt \
    echo "deb https://ppa.launchpadcontent.net/deadsnakes/ppa/ubuntu jammy main" > /etc/apt/sources.list.d/deadsnakes-ppa.list &&\
    /usr/lib/apt/apt-helper download-file 'https://keyserver.ubuntu.com/pks/lookup?op=get&search=0xf23c5a6cf475977595c89f51ba6932366a755776' /etc/apt/trusted.gpg.d/deadsnakes.asc

# install any additional system dependencies
COPY docker/dependencies.txt /tmp/dependencies.txt
RUN --mount=type=cache,target=/var/cache/apt \
    /root/docker-apt-install.sh /tmp/dependencies.txt


##################################################
#
# Build image
#
# Ok, now we have local base image with python and our system dependencies on.
# We'll use this as the base for our builder image, where we'll build and
# install any python packages needed.
#
# We use a separate, disposable build image to avoid carrying the build
# dependencies into the production image.
FROM base-python as builder

# Install any system build dependencies
COPY docker/build-dependencies.txt /tmp/build-dependencies.txt
RUN --mount=type=cache,target=/var/cache/apt \
    /root/docker-apt-install.sh /tmp/build-dependencies.txt

# Install everything in venv for isolation from system python libraries
RUN python3.12 -m venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv/ PATH="/opt/venv/bin:$PATH"

# The cache mount means a) /root/.cache is not in the image, and b) it's preserved
# between docker builds locally, for faster dev rebuild.
COPY requirements.prod.txt /tmp/requirements.prod.txt

# DL3042: using cache mount instead
# DL3013: we always want latest pip/setuptools/wheel, at least for now
# hadolint ignore=DL3042,DL3013
RUN --mount=type=cache,target=/root/.cache \
    /opt/venv/bin/python -m pip install -U pip setuptools wheel && \
    /opt/venv/bin/python -m pip install --no-deps --require-hashes --requirement /tmp/requirements.prod.txt


##################################################
#
# Base project image
#
# Ok, we've built everything we need, build an image with all dependencies but
# no code.
#
# Not including the code at this stage has two benefits:
#
# 1) this image only rebuilds when the handfull of files needed to build metrics-base
#    changes. If we do `COPY . /app` now, this will rebuild when *any* file changes.
#
# 2) Ensures we *have* to mount the volume for dev image, as there's no embedded
#    version of the code. Otherwise, we could end up accidentally using the
#    version of the code included when the prod image was built.
FROM base-python as metrics-base

# Create a non-root metrics user to run the app as
RUN useradd --create-home --user-group metrics

# copy venv over from builder image. These will have root:root ownership, but
# are readable by all.
COPY --from=builder /opt/venv /opt/venv

# Ensure we're using the venv by default
ENV VIRTUAL_ENV=/opt/venv/ PATH="/opt/venv/bin:$PATH"

RUN mkdir /app
WORKDIR /app

# We set command rather than entrypoint, to make it easier to run different
# things from the cli
CMD ["/opt/venv/bin/python", "-m", "metrics.tasks.smoke_test"]

# This may not be necessary, but it probably doesn't hurt
ENV PYTHONPATH=/app

# switch to running as the user
USER metrics


##################################################
#
# Production image
#
# Copy code in, add proper metadata
FROM metrics-base as metrics-prod

# Adjust this metadata to fit project. Note that the base-docker image does set
# some basic metadata.
LABEL org.opencontainers.image.title="metrics" \
      org.opencontainers.image.description="Bennett Institute internal metrics tranformation tool" \
      org.opencontainers.image.source="https://github.com/ebmdatalab/metrics"

# copy application code
COPY metrics /app/metrics
COPY metrics/app.json /app/app.json

# finally, tag with build information. These will change regularly, therefore
# we do them as the last action.
ARG BUILD_DATE=unknown
LABEL org.opencontainers.image.created=$BUILD_DATE
ARG GITREF=unknown
LABEL org.opencontainers.image.revision=$GITREF



##################################################
#
# Dev image
#
# Now we build a dev image from our metrics-dev image. This is basically
# installing dev dependencies and matching local UID/GID. It is expected that
# the current code will be mounted in /app when this is run
#
FROM metrics-base as metrics-dev

# switch back to root to run the install of dev requirements.txt
USER root

# install development requirements
COPY requirements.dev.txt /tmp/requirements.dev.txt
# using cache mount instead
# hadolint ignore=DL3042
RUN --mount=type=cache,target=/root/.cache \
    python -m pip install --requirement /tmp/requirements.dev.txt

# in dev, ensure metrics uid matches host user id
ARG DEV_USERID=1000
ARG DEV_GROUPID=1000
RUN usermod -u $DEV_USERID metrics
# Modify metrics only if group id does not already exist. We run dev
# containers with an explicit group id anyway, so file permissions on the host
# will be correct, and we do not actually rely on named metrics group access to
# anything.
RUN grep -q ":$DEV_GROUPID:" /etc/group || groupmod -g $DEV_GROUPID metrics


# switch back to metrics
USER metrics
