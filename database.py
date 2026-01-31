import sqlite3

def init_db():
    conn = sqlite3.connect('project_copilot.db')
    cursor = conn.cursor()
    
    # 1. Requirements Tablosu (WRICEF)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS requirements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            title TEXT NOT NULL,
            module TEXT,
            complexity TEXT,
            status TEXT DEFAULT 'Draft',
            ai_status TEXT DEFAULT 'Pending',
            effort_days INTEGER,
            summary TEXT
        )
    ''')
    
    # 2. Projeler Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_code TEXT NOT NULL,
            project_name TEXT NOT NULL,
            customer_name TEXT,
            start_date DATE,
            end_date DATE,
            status TEXT DEFAULT 'Planning',
            modules TEXT,
            environment TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 3. Analysis Sessions Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analysis_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            session_name TEXT NOT NULL,
            module TEXT,
            process_name TEXT,
            session_date DATE,
            facilitator TEXT,
            status TEXT DEFAULT 'Planned',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    ''')
    
    # 4. Questions Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            category TEXT,
            question_order INTEGER,
            is_mandatory INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES analysis_sessions(id)
        )
    ''')
    
    # 5. Answers Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER NOT NULL,
            answer_text TEXT,
            answered_by TEXT,
            answered_at TIMESTAMP,
            confidence_score REAL,
            FOREIGN KEY (question_id) REFERENCES questions(id)
        )
    ''')
    
    # 6. FitGap Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fitgap (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            gap_id TEXT NOT NULL,
            process_name TEXT,
            gap_description TEXT,
            impact_area TEXT,
            solution_type TEXT,
            risk_level TEXT,
            effort_estimate INTEGER,
            priority TEXT DEFAULT 'Medium',
            status TEXT DEFAULT 'Identified',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES analysis_sessions(id)
        )
    ''')
    
    # 7. FS/TS Documents Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fs_ts_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            requirement_id INTEGER NOT NULL,
            document_type TEXT,
            version TEXT DEFAULT '1.0',
            content TEXT,
            template_used TEXT,
            status TEXT DEFAULT 'Draft',
            approved_by TEXT,
            approved_at TIMESTAMP,
            file_path TEXT,
            sharepoint_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (requirement_id) REFERENCES requirements(id)
        )
    ''')
    
    # 8. Test Cases Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fs_ts_id INTEGER NOT NULL,
            test_case_id TEXT NOT NULL,
            test_scenario TEXT,
            test_type TEXT,
            preconditions TEXT,
            test_steps TEXT,
            expected_result TEXT,
            status TEXT DEFAULT 'Not Started',
            environment TEXT,
            executed_by TEXT,
            executed_at TIMESTAMP,
            alm_reference TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (fs_ts_id) REFERENCES fs_ts_documents(id)
        )
    ''')
    
    # 9. Audit Log Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT NOT NULL,
            record_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            old_values TEXT,
            new_values TEXT,
            changed_by TEXT,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Ornek veri ekle (requirements tablosu bossa)
    cursor.execute("SELECT COUNT(*) FROM requirements")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO requirements (code, title, module, complexity, status, ai_status, effort_days)
            VALUES ('FS_MM_041', 'Purchase Order Approval Workflow', 'MM', 'Medium', 'In Progress', 'Draft', 8)
        ''')
        cursor.execute('''
            INSERT INTO requirements (code, title, module, complexity, status, ai_status, effort_days)
            VALUES ('FS_SD_012', 'Sales Order Output Management', 'SD', 'Low', 'Ready', 'Full', 3)
        ''')
    
    # Ornek proje ekle (projects tablosu bossa)
    cursor.execute("SELECT COUNT(*) FROM projects")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO projects (project_code, project_name, customer_name, status, modules, environment)
            VALUES ('PRJ-2026-001', 'ACME Corp S/4HANA Migration', 'ACME Corporation', 'Active', 'MM,SD,FI,CO', 'DEV')
        ''')
    
    conn.commit()
    conn.close()
    print("Veritabani basariyla kuruldu!")
    print("Tablolar: requirements, projects, analysis_sessions, questions, answers, fitgap, fs_ts_documents, test_cases, audit_log")

if __name__ == '__main__':
    init_db()
