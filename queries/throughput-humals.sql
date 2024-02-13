WITH
  last_saturday AS (
    SELECT CURRENT_DATE - (1 + CAST(extract(dow FROM CURRENT_DATE) AS INT)) % 7 as the_date
  ),
  throughputs_only AS (
    SELECT time, organisation, repo, author, value
    FROM github_pull_requests
    WHERE name = 'prs_merged'
  ),
  in_timeframe AS (
    SELECT time, organisation, repo, author, value
    FROM throughputs_only
    WHERE $__timeFilter(time)
  ),
  fields_munged AS (
    -- the time field is a timestamp, but we only ever write midnight;
    -- we need to keep it as a timestamp type for bucketing below
    SELECT time as day, organisation||'/'||repo AS repo, author, value as throughput
    FROM in_timeframe
  ),
  dependabot_removed AS (
    SELECT day, repo, author, throughput
    FROM fields_munged
    WHERE author NOT LIKE 'dependabot%'
  ),
  non_dev_op_ignored AS (
    SELECT day, repo, author, throughput
    FROM dependabot_removed
    WHERE NOT (repo = 'ebmdatalab/openprescribing' AND author IN ('richiecroker', 'chrisjwood16'))
  ),
  authors_aggregated AS (
    SELECT day, repo, sum(throughput) as throughput
    FROM non_dev_op_ignored
    GROUP BY day, repo
  ),
  partial_week_ignored AS (
    SELECT day, repo, throughput
    FROM authors_aggregated, last_saturday
    WHERE day < last_saturday.the_date
  ),
  bucketed_in_weeks AS (
    SELECT
      -- label buckets with the (exclusive) end date;
      -- the 'origin' argument can be _any_ Saturday
      time_bucket('1 week', day, last_saturday.the_date) + '7 days' as bucket,
      repo,
      -- aggregate by taking the last value because this is a count, not a gauge
      sum(throughput) as throughput
    FROM
      partial_week_ignored, last_saturday
    GROUP BY bucket, repo
  )
SELECT bucket, repo, throughput
FROM bucketed_in_weeks
ORDER BY bucket DESC, repo
