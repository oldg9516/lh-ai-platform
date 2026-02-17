-- <query name>resolution_rate_by_day</query name>
-- <query description>
-- Daily resolution rate for the last 7 days.
-- Primary KPI: percentage of sessions auto-sent by AI.
-- Handles: eval_decision is lowercase.
-- </query description>
-- <query>
SELECT
  DATE_TRUNC('day', created_at) AS day,
  COUNT(*) AS total_sessions,
  COUNT(*) FILTER (WHERE eval_decision = 'send') AS auto_sent,
  COUNT(*) FILTER (WHERE eval_decision = 'draft') AS drafted,
  COUNT(*) FILTER (WHERE eval_decision = 'escalate') AS escalated,
  ROUND(100.0 * COUNT(*) FILTER (WHERE eval_decision = 'send') / NULLIF(COUNT(*), 0), 2) AS resolution_rate
FROM chat_sessions
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY day
ORDER BY day DESC;
-- </query>

-- <query name>category_breakdown</query name>
-- <query description>
-- Category distribution with resolution and escalation rates.
-- Handles: primary_category values are snake_case lowercase.
-- </query description>
-- <query>
SELECT
  primary_category,
  COUNT(*) AS sessions,
  ROUND(100.0 * COUNT(*) FILTER (WHERE eval_decision = 'send') / NULLIF(COUNT(*), 0), 1) AS auto_send_pct,
  ROUND(100.0 * COUNT(*) FILTER (WHERE eval_decision = 'escalate') / NULLIF(COUNT(*), 0), 1) AS escalation_pct
FROM chat_sessions
GROUP BY primary_category
ORDER BY sessions DESC;
-- </query>

-- <query name>customer_ltv_top20</query name>
-- <query description>
-- Top 20 customers by lifetime value (total spend).
-- Handles: join chain customers → subscriptions → orders via customer_id FK.
-- </query description>
-- <query>
SELECT
  c.email, c.name,
  COUNT(o.id) AS total_orders,
  ROUND(SUM(o.price)::numeric, 2) AS total_spent,
  s.status AS subscription_status,
  s.frequency
FROM customers c
JOIN subscriptions s ON s.customer_id = c.id
LEFT JOIN orders o ON o.customer_id = c.id
GROUP BY c.email, c.name, s.status, s.frequency
ORDER BY total_spent DESC NULLS LAST
LIMIT 20;
-- </query>

-- <query name>subscription_status_distribution</query name>
-- <query description>
-- Subscription status breakdown (Active/Paused/Cancelled).
-- Handles: status values are CAPITALIZED.
-- </query description>
-- <query>
SELECT
  status,
  COUNT(*) AS count,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) AS pct
FROM subscriptions
GROUP BY status
ORDER BY count DESC;
-- </query>

-- <query name>ai_cost_by_category</query name>
-- <query description>
-- Average AI response cost per support category.
-- Handles: cost_usd is NUMERIC(10,6), join via TEXT session_id.
-- </query description>
-- <query>
SELECT
  cs.primary_category,
  COUNT(DISTINCT cs.session_id) AS sessions,
  ROUND(SUM(cm.cost_usd)::numeric, 4) AS total_cost,
  ROUND((SUM(cm.cost_usd) / NULLIF(COUNT(DISTINCT cs.session_id), 0))::numeric, 4) AS avg_cost_per_session
FROM chat_sessions cs
JOIN chat_messages cm ON cm.session_id = cs.session_id
WHERE cm.role = 'assistant'
GROUP BY cs.primary_category
ORDER BY total_cost DESC;
-- </query>

-- <query name>tool_usage_frequency</query name>
-- <query description>
-- Tool usage with success rates and HITL approval stats.
-- </query description>
-- <query>
SELECT
  tool_name,
  COUNT(*) AS executions,
  COUNT(*) FILTER (WHERE status = 'success') AS successful,
  COUNT(*) FILTER (WHERE requires_approval = true) AS needed_approval,
  ROUND(AVG(duration_ms)) AS avg_duration_ms
FROM tool_executions
GROUP BY tool_name
ORDER BY executions DESC;
-- </query>

-- <query name>repeat_customers</query name>
-- <query description>
-- Customers with most support interactions (repeat contacts).
-- Handles: customer_email may be NULL, array_agg for categories.
-- </query description>
-- <query>
SELECT
  cs.customer_email,
  COUNT(*) AS total_sessions,
  COUNT(*) FILTER (WHERE eval_decision = 'escalate') AS escalations,
  array_agg(DISTINCT primary_category) AS categories
FROM chat_sessions cs
WHERE customer_email IS NOT NULL
GROUP BY cs.customer_email
HAVING COUNT(*) > 2
ORDER BY total_sessions DESC
LIMIT 20;
-- </query>

-- <query name>delivery_status_overview</query name>
-- <query description>
-- Delivery status distribution by carrier.
-- </query description>
-- <query>
SELECT
  delivery_status,
  carrier,
  COUNT(*) AS count
FROM tracking_events
GROUP BY delivery_status, carrier
ORDER BY count DESC;
-- </query>
