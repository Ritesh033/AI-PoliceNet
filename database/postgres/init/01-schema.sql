-- AI PoliceNet - PostgreSQL Schema
-- This script runs on initial database creation

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- Users & Authentication
-- ============================================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    registration_id VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(20) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    date_of_birth DATE,
    address TEXT,
    state VARCHAR(100),
    district VARCHAR(100),
    user_type VARCHAR(50) NOT NULL CHECK (user_type IN ('citizen', 'officer', 'inspector', 'admin', 'judge', 'moderator')),
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    permissions JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE user_roles (
    user_id UUID REFERENCES users(id),
    role_id UUID REFERENCES roles(id),
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    assigned_by UUID REFERENCES users(id),
    PRIMARY KEY (user_id, role_id)
);

-- ============================================================================
-- Officers
-- ============================================================================

CREATE TABLE officers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE REFERENCES users(id),
    badge_number VARCHAR(50) UNIQUE NOT NULL,
    batch_number VARCHAR(50),
    department VARCHAR(100),
    designation VARCHAR(100),
    rank VARCHAR(50),
    posting_location VARCHAR(255),
    state VARCHAR(100),
    district VARCHAR(100),
    joining_date DATE,
    integrity_score DECIMAL(5,2) DEFAULT 100.00,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- FIR (First Information Report)
-- ============================================================================

CREATE TABLE firs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fir_number VARCHAR(50) UNIQUE NOT NULL,
    complainant_id UUID REFERENCES users(id),
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    incident_date TIMESTAMPTZ,
    incident_location TEXT,
    incident_state VARCHAR(100),
    incident_district VARCHAR(100),
    category VARCHAR(100),
    severity VARCHAR(20) CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    status VARCHAR(50) DEFAULT 'registered' CHECK (status IN (
        'registered', 'under_review', 'investigation', 'court_referred',
        'resolved', 'closed', 'false_report'
    )),
    assigned_officer_id UUID REFERENCES officers(id),
    ai_risk_score DECIMAL(5,2),
    is_ai_generated BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- FIR records are immutable; amendments require court authorization
CREATE TABLE fir_amendments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fir_id UUID REFERENCES firs(id),
    court_order_id VARCHAR(100) NOT NULL,
    amendment_description TEXT NOT NULL,
    amended_by UUID REFERENCES users(id),
    approved_by_judge UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE fir_status_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fir_id UUID REFERENCES firs(id),
    previous_status VARCHAR(50),
    new_status VARCHAR(50),
    changed_by UUID REFERENCES users(id),
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- Accountability
-- ============================================================================

CREATE TABLE misconduct_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    officer_id UUID REFERENCES officers(id),
    reported_by UUID REFERENCES users(id),
    report_type VARCHAR(50) CHECK (report_type IN (
        'false_fir', 'misconduct', 'corruption', 'abuse_of_power',
        'evidence_tampering', 'phone_seizure', 'misbehavior'
    )),
    description TEXT NOT NULL,
    evidence_ids UUID[],
    status VARCHAR(50) DEFAULT 'pending',
    ai_risk_score DECIMAL(5,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE officer_fines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    officer_id UUID REFERENCES officers(id),
    misconduct_report_id UUID REFERENCES misconduct_reports(id),
    fine_amount DECIMAL(12,2) NOT NULL,
    reason TEXT NOT NULL,
    authorized_by UUID REFERENCES users(id),
    payment_status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE disciplinary_actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    officer_id UUID REFERENCES officers(id),
    action_type VARCHAR(50) CHECK (action_type IN (
        'warning', 'suspension', 'fine', 'demotion', 'termination', 'inquiry'
    )),
    description TEXT NOT NULL,
    authorized_by UUID REFERENCES users(id),
    effective_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- Audit Logs
-- ============================================================================

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Audit logs are append-only (no UPDATE/DELETE permissions)

-- ============================================================================
-- Court Integration
-- ============================================================================

CREATE TABLE court_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fir_id UUID REFERENCES firs(id),
    order_type VARCHAR(50) CHECK (order_type IN (
        'fir_amendment', 'investigation_directive', 'bail',
        'arrest_warrant', 'evidence_request', 'case_closure'
    )),
    order_text TEXT NOT NULL,
    issued_by UUID REFERENCES users(id),
    digital_signature TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- Sessions & OTP
-- ============================================================================

CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    refresh_token TEXT NOT NULL,
    ip_address INET,
    user_agent TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE otp_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    otp_hash VARCHAR(255) NOT NULL,
    purpose VARCHAR(50) DEFAULT 'login',
    attempts INT DEFAULT 0,
    expires_at TIMESTAMPTZ NOT NULL,
    used BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- Default Roles
-- ============================================================================

INSERT INTO roles (name, description, permissions) VALUES
    ('citizen', 'Regular citizen', '["file_complaint", "upload_evidence", "view_own_cases"]'),
    ('officer', 'Police officer', '["view_firs", "update_fir_status", "manage_investigations"]'),
    ('inspector', 'Police inspector', '["view_firs", "assign_officers", "manage_investigations", "review_evidence"]'),
    ('moderator', 'Content moderator', '["review_social_media", "flag_content", "review_evidence"]'),
    ('judge', 'Judiciary member', '["view_cases", "issue_orders", "authorize_amendments"]'),
    ('admin', 'System administrator', '["manage_users", "manage_roles", "view_audit", "system_config"]');

-- ============================================================================
-- Indexes
-- ============================================================================

CREATE INDEX idx_users_registration_id ON users(registration_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_users_user_type ON users(user_type);

CREATE INDEX idx_officers_badge_number ON officers(badge_number);
CREATE INDEX idx_officers_posting_location ON officers(posting_location);
CREATE INDEX idx_officers_integrity_score ON officers(integrity_score);

CREATE INDEX idx_firs_fir_number ON firs(fir_number);
CREATE INDEX idx_firs_status ON firs(status);
CREATE INDEX idx_firs_complainant ON firs(complainant_id);
CREATE INDEX idx_firs_assigned_officer ON firs(assigned_officer_id);
CREATE INDEX idx_firs_created_at ON firs(created_at);
CREATE INDEX idx_firs_incident_state ON firs(incident_state);

CREATE INDEX idx_misconduct_officer ON misconduct_reports(officer_id);
CREATE INDEX idx_misconduct_status ON misconduct_reports(status);

CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_created_at ON audit_logs(created_at);
