-- AI resolution rate: % of sessions auto-sent without human intervention
-- This is the primary KPI for AI effectiveness
--
-- Interpretation:
-- - > 70% = Good (AI handling most queries independently)
-- - 50-70% = Acceptable (room for improvement)
-- - < 50% = Needs attention (too many escalations/drafts)

SELECT
  DATE_TRUNC('day', created_at) as day,
  COUNT(*) as total_sessions,
  COUNT(*) FILTER (WHERE eval_decision = 'send') as auto_sent,
  COUNT(*) FILTER (WHERE eval_decision = 'draft') as drafted,
  COUNT(*) FILTER (WHERE eval_decision = 'escalate') as escalated,
  ROUND(100.0 * COUNT(*) FILTER (WHERE eval_decision = 'send') / COUNT(*), 2) as resolution_rate_pct,
  ROUND(100.0 * COUNT(*) FILTER (WHERE eval_decision = 'escalate') / COUNT(*), 2) as escalation_rate_pct
FROM chat_sessions
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY day
ORDER BY day DESC;
