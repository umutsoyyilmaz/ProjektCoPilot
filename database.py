import sqlite3
import os

def init_db():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'project_copilot.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Requirements Tablosu (WRICEF)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS requirements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            code TEXT NOT NULL,
            title TEXT NOT NULL,
            module TEXT,
            complexity TEXT,
            status TEXT DEFAULT 'Draft',
            ai_status TEXT DEFAULT 'Pending',
            effort_days INTEGER,
            summary TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id)
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
            customer_industry TEXT,
            customer_country TEXT,
            customer_contact TEXT,
            customer_email TEXT,
            deployment_type TEXT,
            implementation_approach TEXT,
            sap_modules TEXT,
            golive_planned DATE,
            golive_actual DATE,
            project_manager TEXT,
            solution_architect TEXT,
            functional_lead TEXT,
            technical_lead TEXT,
            total_budget REAL,
            current_phase TEXT,
            completion_percent INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 3. Analysis Sessions Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analysis_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            scenario_id INTEGER,
            session_name TEXT NOT NULL,
            session_code TEXT,
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
            question_id TEXT,
            question_text TEXT NOT NULL,
            category TEXT,
            question_order INTEGER,
            is_mandatory INTEGER DEFAULT 0,
            answer_text TEXT,
            answered_by TEXT,
            status TEXT DEFAULT 'Open',
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
            project_id INTEGER,
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

    # 10. Scenarios Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scenarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            scenario_id TEXT,
            name TEXT NOT NULL,
            module TEXT,
            description TEXT,
            status TEXT DEFAULT 'Draft',
            level TEXT,
            parent_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    ''')

    # 11. Session Attendees Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS session_attendees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            role TEXT,
            department TEXT,
            email TEXT,
            status TEXT DEFAULT 'Invited',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES analysis_sessions(id)
        )
    ''')

    # 12. Session Agenda Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS session_agenda (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            item_order INTEGER DEFAULT 1,
            topic TEXT,
            description TEXT,
            duration_minutes INTEGER DEFAULT 30,
            presenter TEXT,
            status TEXT DEFAULT 'Planned',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES analysis_sessions(id)
        )
    ''')

    # 13. Meeting Minutes Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS meeting_minutes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            minute_order INTEGER DEFAULT 1,
            topic TEXT,
            discussion TEXT,
            content TEXT,
            key_points TEXT,
            recorded_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES analysis_sessions(id)
        )
    ''')

    # 14. Action Items Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS action_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            project_id INTEGER,
            action_id TEXT,
            title TEXT NOT NULL,
            description TEXT,
            assigned_to TEXT,
            due_date TEXT,
            priority TEXT DEFAULT 'Medium',
            status TEXT DEFAULT 'Open',
            source TEXT,
            related_gap_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES analysis_sessions(id)
        )
    ''')

    # 15. Decisions Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            project_id INTEGER,
            decision_id TEXT,
            topic TEXT,
            description TEXT,
            options_considered TEXT,
            decision_made TEXT,
            rationale TEXT,
            decision_maker TEXT,
            decision_date TEXT,
            impact_areas TEXT,
            status TEXT DEFAULT 'Draft',
            related_gap_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES analysis_sessions(id)
        )
    ''')

    # 16. Risks & Issues Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS risks_issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            project_id INTEGER,
            item_id TEXT,
            title TEXT NOT NULL,
            description TEXT,
            item_type TEXT DEFAULT 'Risk',
            type TEXT DEFAULT 'Risk',
            probability TEXT,
            impact_level TEXT,
            risk_score REAL,
            status TEXT DEFAULT 'Open',
            owner TEXT,
            mitigation TEXT,
            contingency TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES analysis_sessions(id)
        )
    ''')

    # 17. Analyses Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            analysis_type TEXT,
            title TEXT,
            content TEXT,
            status TEXT DEFAULT 'Draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES analysis_sessions(id)
        )
    ''')

    # 18. New Requirements Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS new_requirements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            project_id INTEGER,
            gap_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            module TEXT,
            fit_type TEXT,
            classification TEXT DEFAULT 'Gap',
            priority TEXT DEFAULT 'Medium',
            status TEXT DEFAULT 'Draft',
            conversion_status TEXT DEFAULT 'None',
            converted_item_type TEXT,
            converted_item_id INTEGER,
            converted_at TIMESTAMP,
            converted_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES analysis_sessions(id)
        )
    ''')

    # 19. WRICEF Items Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wricef_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            requirement_id INTEGER,
            code TEXT,
            title TEXT NOT NULL,
            description TEXT,
            wricef_type TEXT,
            module TEXT,
            complexity TEXT,
            effort_days INTEGER,
            status TEXT DEFAULT 'Draft',
            owner TEXT,
            fs_content TEXT,
            ts_content TEXT,
            unit_test_steps TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    ''')

    # 20. Config Items Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            requirement_id INTEGER,
            code TEXT,
            title TEXT NOT NULL,
            description TEXT,
            config_type TEXT,
            module TEXT,
            status TEXT DEFAULT 'Draft',
            owner TEXT,
            config_details TEXT,
            unit_test_steps TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    ''')

    # 21. WRICEF (Legacy) Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wricef (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            wricef_id TEXT,
            title TEXT,
            wricef_type TEXT,
            module TEXT,
            status TEXT DEFAULT 'Draft'
        )
    ''')

    # 22. Test Management Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_management (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            code TEXT,
            test_type TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'Draft',
            owner TEXT,
            source_type TEXT,
            source_id INTEGER,
            steps TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id)
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
    print("Tablolar: requirements, projects, analysis_sessions, questions, answers,")
    print("  fitgap, fs_ts_documents, test_cases, audit_log, scenarios,")
    print("  session_attendees, session_agenda, meeting_minutes, action_items,")
    print("  decisions, risks_issues, analyses, new_requirements,")
    print("  wricef_items, config_items, wricef, test_management")

if __name__ == '__main__':
    init_db()
