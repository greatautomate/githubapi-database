-- GitHub Repository Visibility Bot Database Schema
-- For Render PostgreSQL

-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    is_authorized BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- GitHub APIs table
CREATE TABLE IF NOT EXISTS github_apis (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    api_name VARCHAR(255) NOT NULL,
    github_token TEXT NOT NULL, -- Encrypted with Fernet
    github_username VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, api_name)
);

-- Repositories table
CREATE TABLE IF NOT EXISTS repositories (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    repo_name VARCHAR(255) NOT NULL,
    owner VARCHAR(255) NOT NULL,
    current_visibility VARCHAR(20) NOT NULL CHECK (current_visibility IN ('public', 'private')),
    last_modified TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, repo_name, owner)
);

-- Audit logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    action VARCHAR(255) NOT NULL,
    repository VARCHAR(255) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(50) NOT NULL CHECK (status IN ('success', 'failed'))
);

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
CREATE INDEX IF NOT EXISTS idx_github_apis_user_id ON github_apis(user_id);
CREATE INDEX IF NOT EXISTS idx_github_apis_user_active ON github_apis(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_repositories_user_id ON repositories(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC);

-- Comments for documentation
COMMENT ON TABLE users IS 'Telegram users registered with the bot';
COMMENT ON TABLE github_apis IS 'GitHub API tokens (encrypted) for each user';
COMMENT ON TABLE repositories IS 'Repository visibility tracking';
COMMENT ON TABLE audit_logs IS 'Complete audit trail of all bot actions';

COMMENT ON COLUMN github_apis.github_token IS 'Encrypted GitHub personal access token';
COMMENT ON COLUMN repositories.current_visibility IS 'Current repository visibility: public or private';
COMMENT ON COLUMN audit_logs.status IS 'Operation result: success or failed';
