# 2. Use Sentry Cron monitoring

Date: 2024-06-26

## Status

Accepted

## Context

The metrics tasks run as a dokku-controlled cron job.

There have been instances when this cron job has failed silently due to software or configuration errors.
We would like to know if there have been errors or if the cron job has not run on schedule.

The `dokku logs metrics` command did not reveal any trace of these silent errors.

Sentry is in use for other monitoring of systems within the Bennett Institute.
Sentry [offers](https://docs.sentry.io/platforms/python/crons/) the ability to monitor scheduled cron jobs.
Sentry Cron monitoring allows [check-ins](https://docs.sentry.io/platforms/python/crons/#manual-check-ins)
to be sent at various points in the job's execution with status codes, but not full error messages.

Sentry also offers [error capture](https://docs.sentry.io/product/sentry-basics/integrate-backend/capturing-errors/)
and reporting functionality, which is in use in other Bennett Institute projects.

## Decision

We will use Sentry Cron monitoring to monitor the execution of the metrics cron job on dokku3.

We will not implement Sentry error capture at this point in time.

## Consequences

We will know if the metrics cron job is executing according to schedule, and if there are any errors or not.

We will not know via Sentry what these errors are (if any).
Further manual investigation will be required.
If this becomes a problem in future, we can implement Sentry error capture.
