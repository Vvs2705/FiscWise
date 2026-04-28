-- ContaFlow PostgreSQL Initialization Script
-- This script runs automatically on first container startup

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";      -- UUID generation functions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";       -- Cryptographic functions
CREATE EXTENSION IF NOT EXISTS "vector";         -- pgvector for embeddings (AI/ML)

-- Set timezone to UTC (best practice for multi-region apps)
ALTER DATABASE contaflow_db SET timezone TO 'UTC';

-- Create application user with limited privileges (principle of least privilege)
-- Note: In production, use a separate user with restricted permissions
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'contaflow_app') THEN
        CREATE ROLE contaflow_app WITH LOGIN PASSWORD 'contaflow_app_2026';
    END IF;
END
$$;

-- Grant necessary privileges to application user
GRANT CONNECT ON DATABASE contaflow_db TO contaflow_app;
GRANT USAGE ON SCHEMA public TO contaflow_app;
GRANT CREATE ON SCHEMA public TO contaflow_app;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'ContaFlow database initialized successfully';
    RAISE NOTICE 'Extensions enabled: uuid-ossp, pgcrypto, vector';
    RAISE NOTICE 'Application user created: contaflow_app';
END
$$;
