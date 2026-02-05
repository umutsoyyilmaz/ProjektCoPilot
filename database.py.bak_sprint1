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


def run_migrations():
    """Run database migrations for newreq architecture"""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'project_copilot.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n=== Running NewReq Architecture Migrations ===\n")
    
    try:
        # Check if migrations already applied
        cursor.execute("PRAGMA table_info(scenarios)")
        scenarios_cols = [col[1] for col in cursor.fetchall()]
        
        if 'is_composite' not in scenarios_cols:
            print("1. Adding composite scenario support to scenarios table...")
            cursor.execute("ALTER TABLE scenarios ADD COLUMN is_composite INTEGER DEFAULT 0")
            cursor.execute("ALTER TABLE scenarios ADD COLUMN included_scenario_ids TEXT")
            cursor.execute("ALTER TABLE scenarios ADD COLUMN tags TEXT")
            print("   ✓ Scenarios updated")
        else:
            print("1. Scenarios table already migrated ✓")
        
        # Check new_requirements columns
        cursor.execute("PRAGMA table_info(new_requirements)")
        req_cols = [col[1] for col in cursor.fetchall()]
        
        if 'code' not in req_cols:
            print("2. Enhancing new_requirements table...")
            cursor.execute("ALTER TABLE new_requirements ADD COLUMN code TEXT")
            cursor.execute("ALTER TABLE new_requirements ADD COLUMN analysis_id INTEGER")
            cursor.execute("ALTER TABLE new_requirements ADD COLUMN acceptance_criteria TEXT")
            print("   ✓ New_requirements updated")
        else:
            print("2. New_requirements table already migrated ✓")
        
        # Check wricef_items columns
        cursor.execute("PRAGMA table_info(wricef_items)")
        wricef_cols = [col[1] for col in cursor.fetchall()]
        
        if 'scenario_id' not in wricef_cols:
            print("3. Enhancing wricef_items table...")
            cursor.execute("ALTER TABLE wricef_items ADD COLUMN scenario_id INTEGER")
            cursor.execute("ALTER TABLE wricef_items ADD COLUMN fs_link TEXT")
            cursor.execute("ALTER TABLE wricef_items ADD COLUMN ts_link TEXT")
            cursor.execute("ALTER TABLE wricef_items ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            print("   ✓ Wricef_items updated")
        else:
            print("3. Wricef_items table already migrated ✓")
        
        # Check config_items columns
        cursor.execute("PRAGMA table_info(config_items)")
        config_cols = [col[1] for col in cursor.fetchall()]
        
        if 'scenario_id' not in config_cols:
            print("4. Enhancing config_items table...")
            cursor.execute("ALTER TABLE config_items ADD COLUMN scenario_id INTEGER")
            cursor.execute("ALTER TABLE config_items ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            print("   ✓ Config_items updated")
        else:
            print("4. Config_items table already migrated ✓")
        
        # Create scenario_analyses table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scenario_analyses'")
        if not cursor.fetchone():
            print("5. Creating scenario_analyses table...")
            cursor.execute('''
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
                )
            ''')
            print("   ✓ Scenario_analyses table created")
        else:
            print("5. Scenario_analyses table already exists ✓")
        
        conn.commit()
        print("\n=== Migrations completed successfully! ===\n")
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    init_db()
    run_migrations()
