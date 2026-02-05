-- ===========================================================================
-- ProjektCoPilot — Database Migration Script
-- ===========================================================================
-- Kaynak: newreq.md + Fonksiyonel Tasarım + AI Entegrasyon Tasarımı
-- NOT: Bu dosya referans amaçlıdır. DB oluşturma models.py üzerinden yapılır.
--      Doğrudan SQL gerekirse bu script kullanılabilir.
-- ===========================================================================

CREATE TABLE IF NOT EXISTS project (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'Active',
    phase VARCHAR(20),
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scenario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    level VARCHAR(5),
    tags TEXT,
    is_composite BOOLEAN NOT NULL DEFAULT 0,
    included_scenario_ids JSON,
    parent_scenario_id INTEGER REFERENCES scenario(id),
    sort_order INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'Draft',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, code)
);
CREATE INDEX IF NOT EXISTS ix_scenario_project ON scenario(project_id);

CREATE TABLE IF NOT EXISTS analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_id INTEGER NOT NULL REFERENCES scenario(id) ON DELETE CASCADE,
    code VARCHAR(20) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    owner VARCHAR(50),
    status VARCHAR(20) DEFAULT 'Draft',
    workshop_date DATE,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_analysis_scenario ON analysis(scenario_id);

CREATE TABLE IF NOT EXISTS requirement (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER NOT NULL REFERENCES analysis(id) ON DELETE CASCADE,
    code VARCHAR(20) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    classification VARCHAR(20),
    priority VARCHAR(20),
    acceptance_criteria TEXT,
    conversion_status VARCHAR(20) NOT NULL DEFAULT 'None',
    converted_item_id INTEGER,
    converted_item_type VARCHAR(20),
    converted_at TIMESTAMP,
    converted_by VARCHAR(50),
    status VARCHAR(20) DEFAULT 'Draft',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_requirement_analysis ON requirement(analysis_id);
CREATE INDEX IF NOT EXISTS ix_requirement_classification ON requirement(classification);

CREATE TABLE IF NOT EXISTS wricef_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    scenario_id INTEGER REFERENCES scenario(id) ON DELETE SET NULL,
    requirement_id INTEGER REFERENCES requirement(id) ON DELETE SET NULL,
    code VARCHAR(20) NOT NULL,
    wricef_type VARCHAR(5) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    module VARCHAR(20),
    status VARCHAR(30) NOT NULL DEFAULT 'Backlog',
    owner VARCHAR(50),
    complexity VARCHAR(20),
    estimated_effort_days REAL,
    fs_content TEXT,
    ts_content TEXT,
    unit_test_steps JSON,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, code)
);
CREATE INDEX IF NOT EXISTS ix_wricef_project ON wricef_item(project_id);
CREATE INDEX IF NOT EXISTS ix_wricef_requirement ON wricef_item(requirement_id);

CREATE TABLE IF NOT EXISTS config_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    scenario_id INTEGER REFERENCES scenario(id) ON DELETE SET NULL,
    requirement_id INTEGER REFERENCES requirement(id) ON DELETE SET NULL,
    code VARCHAR(20) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    module VARCHAR(20),
    config_details JSON,
    unit_test_steps JSON,
    status VARCHAR(20) NOT NULL DEFAULT 'Draft',
    owner VARCHAR(50),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, code)
);
CREATE INDEX IF NOT EXISTS ix_config_project ON config_item(project_id);
CREATE INDEX IF NOT EXISTS ix_config_requirement ON config_item(requirement_id);

CREATE TABLE IF NOT EXISTS test_case (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    code VARCHAR(20) NOT NULL,
    test_type VARCHAR(20) NOT NULL,
    title VARCHAR(300) NOT NULL,
    description TEXT,
    module VARCHAR(20),
    status VARCHAR(20) NOT NULL DEFAULT 'Draft',
    owner VARCHAR(50),
    source_type VARCHAR(20),
    source_id INTEGER,
    steps JSON,
    priority VARCHAR(20),
    preconditions TEXT,
    automation_status VARCHAR(20) DEFAULT 'Manual',
    ai_generated BOOLEAN NOT NULL DEFAULT 0,
    ai_confidence_score REAL,
    risk_score REAL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, code)
);
CREATE INDEX IF NOT EXISTS ix_testcase_project ON test_case(project_id);
CREATE INDEX IF NOT EXISTS ix_testcase_type_status ON test_case(test_type, status);
CREATE INDEX IF NOT EXISTS ix_testcase_source ON test_case(source_type, source_id);

CREATE TABLE IF NOT EXISTS test_cycle (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(200) NOT NULL,
    test_type VARCHAR(20) NOT NULL,
    start_date DATE,
    end_date DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'Planned',
    entry_criteria JSON,
    entry_criteria_met BOOLEAN NOT NULL DEFAULT 0,
    exit_criteria JSON,
    exit_criteria_met BOOLEAN NOT NULL DEFAULT 0,
    target_pass_rate REAL,
    target_defect_density REAL,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, code)
);
CREATE INDEX IF NOT EXISTS ix_testcycle_project ON test_cycle(project_id);

CREATE TABLE IF NOT EXISTS test_execution (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_case_id INTEGER NOT NULL REFERENCES test_case(id) ON DELETE CASCADE,
    test_cycle_id INTEGER NOT NULL REFERENCES test_cycle(id) ON DELETE CASCADE,
    code VARCHAR(20) NOT NULL,
    tester VARCHAR(50),
    status VARCHAR(20) NOT NULL DEFAULT 'NotStarted',
    execution_date TIMESTAMP,
    duration_minutes INTEGER,
    evidence JSON,
    step_results JSON,
    notes TEXT,
    environment VARCHAR(20),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_execution_case_cycle ON test_execution(test_case_id, test_cycle_id);

CREATE TABLE IF NOT EXISTS defect (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    code VARCHAR(20) NOT NULL,
    title VARCHAR(300) NOT NULL,
    description TEXT,
    steps_to_reproduce TEXT,
    severity VARCHAR(20),
    priority VARCHAR(20),
    status VARCHAR(20) NOT NULL DEFAULT 'New',
    test_execution_id INTEGER REFERENCES test_execution(id) ON DELETE SET NULL,
    wricef_id INTEGER REFERENCES wricef_item(id) ON DELETE SET NULL,
    assigned_to VARCHAR(50),
    assigned_at TIMESTAMP,
    root_cause VARCHAR(20),
    root_cause_detail TEXT,
    resolution TEXT,
    resolved_at TIMESTAMP,
    sla_deadline TIMESTAMP,
    sla_breached BOOLEAN NOT NULL DEFAULT 0,
    ai_suggested_severity VARCHAR(20),
    ai_severity_confidence REAL,
    ai_root_cause_prediction VARCHAR(20),
    ai_root_cause_confidence REAL,
    ai_similar_defects JSON,
    ai_is_duplicate BOOLEAN,
    ai_duplicate_of_id INTEGER,
    ai_anomaly_flag BOOLEAN NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, code)
);
CREATE INDEX IF NOT EXISTS ix_defect_project ON defect(project_id);
CREATE INDEX IF NOT EXISTS ix_defect_execution ON defect(test_execution_id);
CREATE INDEX IF NOT EXISTS ix_defect_wricef ON defect(wricef_id);
CREATE INDEX IF NOT EXISTS ix_defect_severity_status ON defect(severity, status);

CREATE TABLE IF NOT EXISTS ai_interaction_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(50),
    session_id VARCHAR(100),
    interaction_type VARCHAR(30) NOT NULL,
    related_entity_type VARCHAR(30),
    related_entity_id INTEGER,
    input_text TEXT,
    output_text TEXT,
    model_used VARCHAR(50),
    tokens_in INTEGER,
    tokens_out INTEGER,
    cost_usd REAL,
    user_feedback VARCHAR(20),
    feedback_comment TEXT,
    response_time_ms INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_ai_type_date ON ai_interaction_log(interaction_type, created_at);

CREATE TABLE IF NOT EXISTS ai_embedding (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type VARCHAR(30) NOT NULL,
    entity_id INTEGER NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    embedding_vector JSON NOT NULL,
    metadata JSON,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entity_type, entity_id, content_hash)
);
CREATE INDEX IF NOT EXISTS ix_embedding_entity ON ai_embedding(entity_type, entity_id);

CREATE TABLE IF NOT EXISTS scenario_test_case (
    scenario_id INTEGER NOT NULL REFERENCES scenario(id) ON DELETE CASCADE,
    test_case_id INTEGER NOT NULL REFERENCES test_case(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (scenario_id, test_case_id)
);
