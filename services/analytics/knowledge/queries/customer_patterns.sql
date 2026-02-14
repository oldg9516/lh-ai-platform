-- Customer patterns: Identify customers with repeat issues
-- Helps spot systematic problems or high-touch customers

SELECT
  customer_email,
  COUNT(DISTINCT session_id) as session_count,
  -- Most common category for this customer
  MODE() WITHIN GROUP (ORDER BY primary_category) as most_common_category,
  -- Last interaction date
  MAX(created_at) as last_interaction,
  -- Escalation rate for this customer
  ROUND(100.0 * COUNT(*) FILTER (WHERE eval_decision = 'escalate') / COUNT(*), 2) as customer_escalation_rate
FROM chat_sessions
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY customer_email
-- Show only customers with multiple sessions
HAVING COUNT(DISTINCT session_id) > 1
ORDER BY session_count DESC
LIMIT 50;
