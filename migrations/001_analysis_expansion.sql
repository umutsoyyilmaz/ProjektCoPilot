-- 1.1 Session Attendees
CREATE TABLE IF NOT EXISTS session_attendees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    email TEXT,
    role TEXT,
    department TEXT,
    company TEXT,
    is_required INTEGER DEFAULT 1,
    attendance_status TEXT DEFAULT 'Invited',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES analysis_sessions(id)
);

-- 1.2 Session Agenda
CREATE TABLE IF NOT EXISTS session_agenda (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    item_order INTEGER DEFAULT 1,
    topic TEXT NOT NULL,
    description TEXT,
    duration_minutes INTEGER DEFAULT 30,
    presenter TEXT,
    status TEXT DEFAULT 'Planned',
    actual_duration INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES analysis_sessions(id)
);

-- 1.3 Meeting Minutes
CREATE TABLE IF NOT EXISTS meeting_minutes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    minute_order INTEGER DEFAULT 1,
    topic TEXT,
    discussion TEXT,
    key_points TEXT,
    recorded_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES analysis_sessions(id)
);

-- 1.4 Action Items
CREATE TABLE IF NOT EXISTS action_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    action_id TEXT,
    title TEXT NOT NULL,
    description TEXT,
    assigned_to TEXT,
    assigned_email TEXT,
    due_date DATE,
    priority TEXT DEFAULT 'Medium',
    status TEXT DEFAULT 'Open',
    completion_date DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES analysis_sessions(id)
);

-- 1.5 Decisions
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    project_id INTEGER,
    decision_id TEXT,
    topic TEXT NOT NULL,
    description TEXT,
    options_considered TEXT,
    decision_made TEXT NOT NULL,
    rationale TEXT,
    decision_maker TEXT,
    decision_date DATE,
    impact_areas TEXT,
    status TEXT DEFAULT 'Draft',
    related_gap_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES analysis_sessions(id),
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- 1.6 Risks and Issues
CREATE TABLE IF NOT EXISTS risks_issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    project_id INTEGER,
    item_id TEXT,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT,
    impact TEXT DEFAULT 'Medium',
    probability TEXT DEFAULT 'Medium',
    risk_score INTEGER,
    mitigation_plan TEXT,
    contingency_plan TEXT,
    owner TEXT,
    owner_email TEXT,
    status TEXT DEFAULT 'Open',
    target_resolution_date DATE,
    actual_resolution_date DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES analysis_sessions(id),
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- 1.7 Attachments
CREATE TABLE IF NOT EXISTS attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    project_id INTEGER,
    related_type TEXT,
    related_id INTEGER,
    file_name TEXT NOT NULL,
    file_type TEXT,
    file_size INTEGER,
    file_path TEXT,
    description TEXT,
    uploaded_by TEXT,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES analysis_sessions(id),
    FOREIGN KEY (project_id) REFERENCES projects(id)
);
