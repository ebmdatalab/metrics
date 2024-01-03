# 2. Use Timescale with PostgreSQL for Metrics

Date: 2023-11-24

## Status

Accepted

## Context

We need to store certain metrics data, such as details about pull requests and issues from GitHub and support requests from Slack. We're unable to get this information on demand using the APIs, because there's either no support with an existing Grafana plugin, it's not fast enough or it doesn't provide all the information we need.

In same cases, we need to store a large amount of timeseries data. The Timescale extension to PostgreSQL allows us to query that data in a very performant way and provides some nice functions so that we can perform operations, like bucketing the data, on the database server rather than when loading the dashboard.

## Decision

We will use PostgreSQL with the Timescale extension to store our metrics data.

## Consequences

We'll be able to store all the different types of data that are needed for our dashboards.

The PostgreSQL database will be hosted using a managed Digital Ocean service and backed up using Snapshooter. We believe this will keep the operational burden to a minimum.
