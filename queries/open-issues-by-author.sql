WITH
  last_saturday AS (
    SELECT CURRENT_DATE - (1 + CAST(extract(dow FROM CURRENT_DATE) AS INT)) % 7 as the_date
  ),
  issues AS (
    SELECT time, organisation, repo, author, count
    FROM github_issues
  ),
  in_timeframe AS (
    SELECT time, organisation, repo, author, count
    FROM issues
    WHERE $__timeFilter(time)
  ),
  fields_munged AS (
    -- the time field is a timestamp, but we only ever write midnight;
    -- we need to keep it as a timestamp type for bucketing below
    SELECT time as day, organisation||'/'||repo AS repo, author, count
    FROM in_timeframe
  ),
  repos_aggregated AS (
    SELECT day, author, sum(count) as count
    FROM fields_munged
    GROUP BY day, author
  ),
  partial_week_ignored AS (
    SELECT day, author, count
    FROM repos_aggregated, last_saturday
    WHERE day < last_saturday.the_date
  ),
  bucketed_in_weeks AS (
    SELECT
      -- label buckets with the (exclusive) end date;
      -- the 'origin' argument can be _any_ Saturday
      time_bucket('1 week', day, last_saturday.the_date) + '7 days' as bucket,
      author,
      -- aggregate by taking the last value because this is a gauge, not a count
      last(count, day) as count
    FROM
      partial_week_ignored, last_saturday
    GROUP BY bucket, author
  )
SELECT bucket, author, count
FROM bucketed_in_weeks
ORDER BY bucket DESC, author
