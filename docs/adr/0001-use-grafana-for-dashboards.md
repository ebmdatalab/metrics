# 1. Record architecture decisions

Date: 2023-11-16

## Status

Accepted

## Context

As a requirement for the [Metrics and Dashboards Initiative](https://docs.google.com/document/d/1VTNfY2Ezv4wxWUAFGhCeOHns285tko-AY0pX2Eo7gTc/edit#heading=h.mnb03peyeng9), we need to be able to display metrics and graphs (in particular, timeseries graphs) to a variety of people across the Bennett Institute.

We carried out a couple of spikes ([1](https://github.com/opensafely-core/job-runner/issues/649), [2](https://github.com/opensafely-core/job-server/pull/3578)) to assess how many of these use cases could be fullfilled by Grafana (or other solutions) and how easy it was to setup and use.

## Decision

To use a self-hosted Grafana instance for the dashboards for the product, system and delivery metrics. To use a managed Digital Ocean Postgres database for the Grafana data.

## Consequences

We considered a few alternatives, such as Honeycomb (which we're already using for opentelemetry data) and datasette (good for visualising sqlite data). However, we felt that Grafana and its plugin ecosystem offered a good selection of features that would allow us to meet the objectives for all three areas (product, system and delivery) within a reasonable timeframe. We believe that self-hosting Grafana, backed by a managed Digital Ocean database, will be low maintenance. We may wish to consider alternatives, such as Grafana Cloud, if that turns out not to be the case.

In future, we may want to use more specialised tools for the three different areas. For example, with the product dashboards, a business intellience tool, such as [Apache Superset](https://superset.apache.org/) or [Metabase](https://www.metabase.com/) may be required to allow easier editing of data visualisations by non-developers and for an improved ability to drill down into the data. We may also want to consider specialised tooling such as prometheus to improve the system dashboards.
