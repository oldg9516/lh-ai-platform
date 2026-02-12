-- Analytics views

CREATE VIEW v_session_stats AS
SELECT
    DATE_TRUNC('day', created_at) AS day,
    primary_category,
    channel,
    COUNT(*) AS total_sessions,
    COUNT(*) FILTER (WHERE status = 'resolved') AS resolved,
    COUNT(*) FILTER (WHERE status = 'escalated') AS escalated,
    AVG(first_response_time_ms) AS avg_first_response_ms,
    AVG(resolution_time_seconds) AS avg_resolution_sec,
    AVG(csat_score) AS avg_csat
FROM chat_sessions
GROUP BY 1, 2, 3;

CREATE VIEW v_cost_by_category AS
SELECT
    cs.primary_category,
    COUNT(DISTINCT cs.id) AS sessions,
    SUM(cm.cost_usd) AS total_cost,
    AVG(cm.cost_usd) AS avg_cost_per_message,
    SUM(cm.cost_usd) / NULLIF(COUNT(DISTINCT cs.id), 0) AS avg_cost_per_session
FROM chat_sessions cs
JOIN chat_messages cm ON cm.session_id = cs.session_id
WHERE cm.role = 'assistant'
GROUP BY 1;

CREATE VIEW v_pipeline_funnel AS
SELECT
    cs.primary_category,
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE cs.eval_decision = 'send') AS auto_sent,
    COUNT(*) FILTER (WHERE cs.eval_decision = 'draft') AS drafted,
    COUNT(*) FILTER (WHERE cs.eval_decision = 'escalate') AS escalated,
    ROUND(
        COUNT(*) FILTER (WHERE cs.eval_decision = 'send') * 100.0 / NULLIF(COUNT(*), 0),
        1
    ) AS auto_send_rate
FROM chat_sessions cs
WHERE cs.created_at >= NOW() - INTERVAL '30 days'
GROUP BY 1;

-- Grant views to service_role
GRANT SELECT ON v_session_stats TO service_role;
GRANT SELECT ON v_cost_by_category TO service_role;
GRANT SELECT ON v_pipeline_funnel TO service_role;
