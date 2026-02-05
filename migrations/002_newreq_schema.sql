-- Migration 002: NewReq Architecture Schema Updates
-- Date: 2026-02-05
-- Purpose: Align database schema with newreq.md specification

-- 1. SCENARIOS: Add composite scenario support
ALTER TABLE scenarios ADD COLUMN is_composite INTEGER DEFAULT 0;
ALTER TABLE scenarios ADD COLUMN included_scenario_ids TEXT; -- JSON array of scenario IDs
ALTER TABLE scenarios ADD COLUMN tags TEXT; -- Process/module tags

-- 2. NEW_REQUIREMENTS: Add missing columns and improve structure
ALTER TABLE new_requirements ADD COLUMN code TEXT; -- REQ-001 format
ALTER TABLE new_requirements ADD COLUMN analysis_id INTEGER; -- FK to analyses (will replace session_id)
ALTER TABLE new_requirements ADD COLUMN acceptance_criteria TEXT;

-- 3. WRICEF_ITEMS: Add scenario linkage and missing fields
ALTER TABLE wricef_items ADD COLUMN scenario_id INTEGER; -- FK to scenarios
ALTER TABLE wricef_items ADD COLUMN fs_link TEXT; -- External FS document link
ALTER TABLE wricef_items ADD COLUMN ts_link TEXT; -- External TS document link
ALTER TABLE wricef_items ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- 4. CONFIG_ITEMS: Add scenario linkage and updated_at
ALTER TABLE config_items ADD COLUMN scenario_id INTEGER;
ALTER TABLE config_items ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- 5. Create new ANALYSES table (scenario-based, not session-based)
CREATE TABLE IF NOT EXISTS scenario_analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_id INTEGER NOT NULL,
    code TEXT UNIQUE,
    title TEXT NOT NULL,
    description TEXT,
    owner TEXT,
    status TEXT DEFAULT 'Draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (scenario_id) REFERENCES scenarios(id)
);

-- 6. Rename old analyses to avoid confusion (optional - for clarity)
-- The old 'analyses' table is session-based and serves different purpose
-- We keep it for backward compatibility but new code uses 'scenario_analyses'

-- Note: Data migration will be handled separately
-- - new_requirements.session_id needs mapping to analysis_id
-- - fitgap data should be migrated to new_requirements with classification='Gap'
