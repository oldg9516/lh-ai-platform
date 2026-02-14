-- Analytics read-only user for analytics service
-- This user has SELECT-only permissions on all tables for safe querying

-- Create read-only user
CREATE USER analytics_readonly WITH PASSWORD 'analytics_pass';

-- Grant connection to database
GRANT CONNECT ON DATABASE postgres TO analytics_readonly;

-- Grant schema usage
GRANT USAGE ON SCHEMA public TO analytics_readonly;

-- Grant SELECT on all existing tables
GRANT SELECT ON ALL TABLES IN SCHEMA public TO analytics_readonly;

-- Grant SELECT on all future tables (auto-grant)
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO analytics_readonly;

-- Verify grants
\du analytics_readonly
