-- Category distribution: Which types of questions are customers asking most?
-- Helps identify training needs and common pain points

SELECT
  primary_category as category,
  COUNT(*) as count,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage,
  -- Resolution rate per category
  ROUND(100.0 * COUNT(*) FILTER (WHERE eval_decision = 'send') / COUNT(*), 2) as category_resolution_rate,
  -- Average response time per category
  ROUND(AVG(first_response_time_ms), 0) as avg_response_time_ms
FROM chat_sessions
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY primary_category
ORDER BY count DESC;
