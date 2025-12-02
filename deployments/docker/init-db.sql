-- Initialize database for Python API Base
-- This script runs on first PostgreSQL startup
-- Includes Core (Users, RBAC) and Example System tables

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE api_db TO api_user;

-- ============================================
-- CORE TABLES (Permanent - Do Not Remove)
-- ============================================

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    username VARCHAR(50) UNIQUE,
    display_name VARCHAR(100),
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_verified BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE,
    version INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);
CREATE INDEX IF NOT EXISTS ix_users_username ON users(username);
CREATE INDEX IF NOT EXISTS ix_users_active ON users(is_active);

-- Roles table
CREATE TABLE IF NOT EXISTS roles (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    permissions JSONB NOT NULL DEFAULT '[]',
    is_system BOOLEAN NOT NULL DEFAULT false,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_roles_name ON roles(name);
CREATE INDEX IF NOT EXISTS ix_roles_active ON roles(is_active);

-- User Roles junction table
CREATE TABLE IF NOT EXISTS user_roles (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id VARCHAR(36) NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    assigned_by VARCHAR(36),
    UNIQUE(user_id, role_id)
);

CREATE INDEX IF NOT EXISTS ix_user_roles_user_id ON user_roles(user_id);
CREATE INDEX IF NOT EXISTS ix_user_roles_role_id ON user_roles(role_id);

-- ============================================
-- SEED DATA: Default Roles
-- ============================================

INSERT INTO roles (id, name, description, permissions, is_system, is_active)
VALUES 
    (uuid_generate_v4()::text, 'admin', 'Full system administrator', 
     '["read", "write", "delete", "admin", "manage_users", "manage_roles", "view_audit", "export_data"]'::jsonb, 
     true, true),
    (uuid_generate_v4()::text, 'user', 'Standard user with read/write access', 
     '["read", "write"]'::jsonb, 
     true, true),
    (uuid_generate_v4()::text, 'viewer', 'Read-only access', 
     '["read"]'::jsonb, 
     true, true),
    (uuid_generate_v4()::text, 'moderator', 'Content moderator', 
     '["read", "write", "delete", "view_audit"]'::jsonb, 
     true, true)
ON CONFLICT (name) DO NOTHING;

-- ============================================
-- SEED DATA: Admin User (password: Admin123!)
-- ============================================

DO $$
DECLARE
    admin_user_id VARCHAR(36);
    admin_role_id VARCHAR(36);
BEGIN
    -- Create admin user if not exists
    INSERT INTO users (id, email, password_hash, display_name, is_active, is_verified)
    VALUES (
        uuid_generate_v4()::text,
        'admin@example.com',
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.G8X0K8K8K8K8K8', -- bcrypt hash
        'System Admin',
        true,
        true
    )
    ON CONFLICT (email) DO NOTHING
    RETURNING id INTO admin_user_id;

    -- Get admin role ID
    SELECT id INTO admin_role_id FROM roles WHERE name = 'admin';

    -- Assign admin role if user was created
    IF admin_user_id IS NOT NULL AND admin_role_id IS NOT NULL THEN
        INSERT INTO user_roles (id, user_id, role_id)
        VALUES (uuid_generate_v4()::text, admin_user_id, admin_role_id)
        ON CONFLICT (user_id, role_id) DO NOTHING;
    END IF;
END $$;

-- ============================================
-- EXAMPLE TABLES (Remove for production)
-- See docs/example-system-deactivation.md
-- ============================================

-- Items example table
CREATE TABLE IF NOT EXISTS items (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL DEFAULT 0,
    quantity INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    version INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS ix_items_name ON items(name);
CREATE INDEX IF NOT EXISTS ix_items_active ON items(is_active);

-- Pedidos example table
CREATE TABLE IF NOT EXISTS pedidos (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    cliente_nome VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pendente',
    total DECIMAL(10, 2) NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_pedidos_status ON pedidos(status);

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'Database initialized for Python API Base';
    RAISE NOTICE '- Core: Users, Roles, User_Roles tables created';
    RAISE NOTICE '- Examples: Items, Pedidos tables created';
    RAISE NOTICE '- Default roles seeded (admin, user, viewer, moderator)';
    RAISE NOTICE '- Admin user created: admin@example.com';
END $$;
