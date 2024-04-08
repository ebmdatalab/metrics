WITH
  last_saturday AS (
    SELECT CURRENT_DATE - (1 + CAST(extract(dow FROM CURRENT_DATE) AS INT)) % 7 as the_date
  ),
  old_prs_only AS (
    SELECT time, organisation, repo, author, is_content, value
    FROM github_pull_requests
    WHERE name = 'queue_older_than_7_days'
  ),
  in_timeframe AS (
    SELECT time, organisation, repo, author, is_content, value
    FROM old_prs_only
    WHERE $__timeFilter(time)
  ),
  fields_munged AS (
    -- the time field is a timestamp, but we only ever write midnight;
    -- we need to keep it as a timestamp type for bucketing below
    SELECT time as day, organisation||'/'||repo AS repo, author, is_content, value as num_prs
    FROM in_timeframe
  ),
  dependabot_removed AS (
    SELECT day, repo, author, is_content, num_prs
    FROM fields_munged
    WHERE author NOT LIKE 'dependabot%'
  ),
  content_ignored AS (
    SELECT day, repo, author, num_prs
    FROM dependabot_removed
    WHERE NOT is_content
  ),
  authors_aggregated AS (
    SELECT day, repo, sum(num_prs) as num_prs
    FROM content_ignored
    GROUP BY day, repo
  ),
  partial_week_ignored AS (
    SELECT day, repo, num_prs
    FROM authors_aggregated, last_saturday
    WHERE day < last_saturday.the_date
  ),
  bucketed_in_weeks AS (
    SELECT
      -- label buckets with the (exclusive) end date;
      -- the 'origin' argument can be _any_ Saturday
      time_bucket('1 week', day, last_saturday.the_date) + '7 days' as bucket,
      repo,
      -- aggregate by taking the last value because this is a gauge, not a count
      last(num_prs, day) as num_prs
    FROM
      partial_week_ignored, last_saturday
    GROUP BY bucket, repo
  )
SELECT repo as "Repo", num_prs AS "Old PRs"
FROM bucketed_in_weeks
ORDER BY bucket DESC, num_prs DESC
LIMIT 5
