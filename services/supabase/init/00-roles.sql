-- PostgREST roles for Supabase-compatible API
-- These roles are used by PostgREST to handle JWT-based auth.

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- anon: unauthenticated requests
CREATE ROLE anon NOLOGIN;

-- service_role: server-side requests (bypasses RLS)
CREATE ROLE service_role NOLOGIN BYPASSRLS;

-- supabase_admin: used by Supabase Studio / postgres-meta
CREATE ROLE supabase_admin LOGIN SUPERUSER PASSWORD 'postgres';

-- authenticator: PostgREST connects as this role, then switches to anon/service_role
CREATE ROLE authenticator NOINHERIT LOGIN PASSWORD 'authenticator';
GRANT anon TO authenticator;
GRANT service_role TO authenticator;
