-- Grant permissions to PostgREST roles

GRANT USAGE ON SCHEMA public TO anon, service_role;

-- service_role gets full access (used by AI Engine via supabase-py)
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;

-- Future tables/sequences also get granted automatically
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO service_role;

-- anon gets read-only on specific tables (not used currently, but set up for future)
GRANT SELECT ON ai_answerer_instructions TO anon;
