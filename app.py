from flask import Flask, render_template, jsonify, request
from datetime import datetime, date
import sqlite3
import os

from models import db, Project, Scenario, Requirement, WricefItem, ConfigItem, TestCase, Analysis

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), 'project_copilot.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{DB_PATH}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def parse_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None

def generate_auto_id(project_id, item_type):
    """
    Proje bazlı otomatik ID üretir
    item_type: Q (Question), G (Gap), D (Decision), R (Risk), I (Issue), A (Action), W (Workshop)
    """
    conn = get_db_connection()
    
    # Proje kodunu al
    project = conn.execute("SELECT project_code FROM projects WHERE id = ?", (project_id,)).fetchone()
    project_code = project["project_code"] if project else f"P{project_id}"
    
    # Tabloya göre sayacı bul
    table_map = {
        "Q": ("questions", "question_id"),
        "G": ("fitgap", "gap_id"),
        "D": ("decisions", "decision_id"),
        "R": ("risks_issues", "item_id"),
        "I": ("risks_issues", "item_id"),
        "A": ("action_items", "action_id"),
        "W": ("analysis_sessions", "session_code"),
        "S": ("scenarios", "scenario_id"),
        "WR": ("wricef", "wricef_id"),
        "C": ("configs", "config_id"),
    }
    
    if item_type not in table_map:
        conn.close()
        return None
    
    table, id_column = table_map[item_type]
    
    # Bu proje için bu tipteki son ID yi bul
    pattern = f"{project_code}-{item_type}%"
    
    if table == "risks_issues":
        type_filter = "Risk" if item_type == "R" else "Issue"
        result = conn.execute(f"SELECT {id_column} FROM {table} WHERE {id_column} LIKE ? AND type = ? ORDER BY id DESC LIMIT 1", (pattern, type_filter)).fetchone()
    elif table == "analysis_sessions":
        result = conn.execute(f"SELECT session_code FROM {table} WHERE project_id = ? ORDER BY id DESC LIMIT 1", (project_id,)).fetchone()
    else:
        result = conn.execute(f"SELECT {id_column} FROM {table} WHERE {id_column} LIKE ? ORDER BY id DESC LIMIT 1", (pattern,)).fetchone()
    
    conn.close()
    
    # Yeni numara hesapla
    if result and result[0]:
        try:
            last_num = int(result[0].split("-")[-1][1:])
            new_num = last_num + 1
        except:
            new_num = 1
    else:
        new_num = 1
    
    return f"{project_code}-{item_type}{new_num:03d}"

@app.route('/')
def index():
    try:
        conn = get_db_connection()
        
        # Tüm requirements (Requirements sayfası için)
        requirements = conn.execute('SELECT * FROM requirements').fetchall()
        
        # Recent Activities (Son 5 değişiklik)
        recent_activities = conn.execute('''
            SELECT * FROM requirements 
            ORDER BY id DESC 
            LIMIT 5
        ''').fetchall()
        
        conn.close()
        return render_template('index.html', 
                             requirements=requirements,
                             recent_activities=recent_activities)
    except Exception as e:
        return f"Veritabanı hatası: {e}"
@app.route('/api/requirements', methods=['GET'])
def get_requirements():
    """Tum requirementlari listele"""
    project_id = request.args.get('project_id')
    try:
        conn = get_db_connection()
        if project_id:
            requirements = conn.execute('SELECT * FROM requirements WHERE project_id = ? ORDER BY id DESC', (project_id,)).fetchall()
        else:
            requirements = conn.execute('SELECT * FROM requirements ORDER BY id DESC').fetchall()
        conn.close()
        return jsonify([dict(row) for row in requirements])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/requirements', methods=['POST'])
def add_requirement():
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO requirements (project_id, code, title, module, complexity, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (data.get('project_id'), data['code'], data['title'], data['module'], data['complexity'], 'Draft'))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# EKSİK OLAN VE SORUNA YOL AÇAN KISIM BURASIYDI:
@app.route('/api/requirements/<int:req_id>')
def get_requirement_detail(req_id):
    try:
        conn = get_db_connection()
        requirement = conn.execute('SELECT * FROM requirements WHERE id = ?', (req_id,)).fetchone()
        conn.close()
        if requirement:
            return jsonify(dict(requirement))
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    return jsonify({"reply": f"Mesajınızı aldım: '{data.get('message')}'"})

# ============== PROJECTS API ==============

@app.route('/api/projects', methods=['GET'])
def get_projects():
    """Tum projeleri listele"""
    try:
        projects = Project.query.order_by(Project.created_at.desc()).all()
        return jsonify([project.to_dict() for project in projects])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/projects", methods=["POST"])
def add_project():
    try:
        data = request.json
        project = Project(
            code=data.get("project_code"),
            name=data.get("project_name"),
            description=data.get("description"),
            status=data.get("status", "Planning"),
            customer_name=data.get("customer_name"),
            customer_industry=data.get("customer_industry"),
            customer_country=data.get("customer_country"),
            customer_contact=data.get("customer_contact"),
            customer_email=data.get("customer_email"),
            deployment_type=data.get("deployment_type"),
            implementation_approach=data.get("implementation_approach"),
            sap_modules=data.get("sap_modules"),
            start_date=parse_date(data.get("start_date")),
            golive_planned=parse_date(data.get("golive_planned")),
            golive_actual=parse_date(data.get("golive_actual")),
            project_manager=data.get("project_manager"),
            solution_architect=data.get("solution_architect"),
            functional_lead=data.get("functional_lead"),
            technical_lead=data.get("technical_lead"),
            total_budget=data.get("total_budget"),
            phase=data.get("current_phase"),
            completion_percent=data.get("completion_percent", 0)
        )
        db.session.add(project)
        db.session.commit()
        new_id = project.id
        return jsonify({"status": "success", "id": new_id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/projects/<int:project_id>', methods=['GET'])
def get_project_detail(project_id):
    """Tek bir projenin detayini getir"""
    try:
        project = Project.query.get(project_id)
        if project:
            return jsonify(project.to_dict())
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/projects/<int:id>", methods=["PUT"])
def update_project(id):
    try:
        data = request.json
        project = Project.query.get(id)
        if not project:
            return jsonify({"error": "Not found"}), 404
        project.code = data.get("project_code", project.code)
        project.name = data.get("project_name", project.name)
        project.description = data.get("description", project.description)
        project.status = data.get("status", project.status)
        project.customer_name = data.get("customer_name", project.customer_name)
        project.customer_industry = data.get("customer_industry", project.customer_industry)
        project.customer_country = data.get("customer_country", project.customer_country)
        project.customer_contact = data.get("customer_contact", project.customer_contact)
        project.customer_email = data.get("customer_email", project.customer_email)
        project.deployment_type = data.get("deployment_type", project.deployment_type)
        project.implementation_approach = data.get("implementation_approach", project.implementation_approach)
        project.sap_modules = data.get("sap_modules", project.sap_modules)
        project.start_date = parse_date(data.get("start_date")) or project.start_date
        project.golive_planned = parse_date(data.get("golive_planned")) or project.golive_planned
        project.golive_actual = parse_date(data.get("golive_actual")) or project.golive_actual
        project.project_manager = data.get("project_manager", project.project_manager)
        project.solution_architect = data.get("solution_architect", project.solution_architect)
        project.functional_lead = data.get("functional_lead", project.functional_lead)
        project.technical_lead = data.get("technical_lead", project.technical_lead)
        project.total_budget = data.get("total_budget", project.total_budget)
        project.phase = data.get("current_phase", project.phase)
        project.completion_percent = data.get("completion_percent", project.completion_percent)
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route("/api/projects/<int:id>", methods=["DELETE"])
def delete_project(id):
    try:
        deleted = Project.query.filter(Project.id == id).delete()
        if deleted == 0:
            return jsonify({"error": "Not found"}), 404
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# ============== ANALYSIS SESSIONS API ==============

@app.route('/api/sessions', methods=['GET'])
@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    """Tum analiz oturumlarini listele"""
    project_id = request.args.get('project_id')
    try:
        conn = get_db_connection()
        if project_id:
            sessions = conn.execute("""
                SELECT s.*, p.project_name, sc.name as scenario_name, sc.scenario_id as scenario_code
                FROM analysis_sessions s
                LEFT JOIN projects p ON s.project_id = p.id
                LEFT JOIN scenarios sc ON s.scenario_id = sc.id
                WHERE s.project_id = ?
                ORDER BY s.created_at DESC
            """, (project_id,)).fetchall()
        else:
            sessions = conn.execute("""
                SELECT s.*, p.project_name, sc.name as scenario_name, sc.scenario_id as scenario_code
                FROM analysis_sessions s
                LEFT JOIN projects p ON s.project_id = p.id
                LEFT JOIN scenarios sc ON s.scenario_id = sc.id
                ORDER BY s.created_at DESC
            """).fetchall()
        conn.close()
        return jsonify([dict(row) for row in sessions])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/sessions/<int:session_id>', methods=['GET'])
def get_session_detail(session_id):
    """Tek bir session detayi"""
    try:
        conn = get_db_connection()
        session = conn.execute("""
            SELECT s.*, p.project_name, sc.name as scenario_name, sc.scenario_id as scenario_code
            FROM analysis_sessions s
            LEFT JOIN projects p ON s.project_id = p.id
            LEFT JOIN scenarios sc ON s.scenario_id = sc.id
            WHERE s.id = ?
        """, (session_id,)).fetchone()
        conn.close()
        if session:
            return jsonify(dict(session))
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/sessions', methods=['POST'])
def add_session():
    """Yeni analiz oturumu ekle"""
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO analysis_sessions (project_id, scenario_id, session_name, module, process_name, facilitator, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (data['project_id'], data.get('scenario_id'), data['session_name'], data.get('module'), 
              data.get('process_name'), data.get('facilitator'), data.get('status', 'Planned'), data.get('notes')))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============== QUESTIONS API ==============

@app.route('/api/questions', methods=['GET'])
def get_questions():
    """Sorulari listele"""
    session_id = request.args.get('session_id')
    try:
        conn = get_db_connection()
        if session_id:
            questions = conn.execute('''
                SELECT q.*, a.answer_text
                FROM questions q
                LEFT JOIN answers a ON q.id = a.question_id
                WHERE q.session_id = ?
                ORDER BY q.created_at ASC
            ''', (session_id,)).fetchall()
        else:
            questions = conn.execute('''
                SELECT q.*, a.answer_text
                FROM questions q
                LEFT JOIN answers a ON q.id = a.question_id
                ORDER BY q.created_at DESC
            ''').fetchall()
        conn.close()
        return jsonify([dict(row) for row in questions])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/questions", methods=["POST"])
def add_question():
    try:
        data = request.json
        session_id = data.get("session_id")
        conn = get_db_connection()
        
        # Session dan project_id al
        session = conn.execute("SELECT project_id FROM analysis_sessions WHERE id = ?", (session_id,)).fetchone()
        project_id = session["project_id"] if session else None
        
        # Otomatik ID uret
        auto_id = generate_auto_id(project_id, "Q") if project_id else None
        
        cursor = conn.execute("""
            INSERT INTO questions (session_id, question_id, question_text, answer_text, status, assigned_to, due_date, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime("now"))
        """, (session_id, auto_id, data.get("question_text"), data.get("answer_text"),
              data.get("status", "Open"), data.get("assigned_to"), data.get("due_date")))
        
        conn.commit()
        conn.close()
        return jsonify({"success": True, "id": cursor.lastrowid, "question_id": auto_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# ============== FITGAP API ==============

@app.route('/api/fitgap', methods=['GET'])
def get_fitgap():
    """Tum FitGap kayitlarini listele"""
    session_id = request.args.get('session_id')
    try:
        conn = get_db_connection()
        if session_id:
            gaps = conn.execute('SELECT * FROM fitgap WHERE session_id = ? ORDER BY created_at DESC', (session_id,)).fetchall()
        else:
            gaps = conn.execute('SELECT * FROM fitgap ORDER BY created_at DESC').fetchall()
        conn.close()
        return jsonify([dict(row) for row in gaps])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/fitgap", methods=["POST"])
def add_fitgap():
    try:
        data = request.json
        session_id = data.get("session_id")
        conn = get_db_connection()
        
        # Session dan project_id al
        session = conn.execute("SELECT project_id FROM analysis_sessions WHERE id = ?", (session_id,)).fetchone()
        project_id = session["project_id"] if session else None
        
        # Otomatik ID uret
        auto_id = generate_auto_id(project_id, "G") if project_id else None
        
        conn.execute("""
            INSERT INTO fitgap (session_id, gap_id, process_name, gap_description, requirement_description,
            sap_standard_solution, impact_area, solution_type, priority, status, decision_rationale, module)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (session_id, auto_id, data.get("process_name"), data.get("description"),
              data.get("requirement_description"), data.get("sap_standard_solution"),
              data.get("impact_area"), data.get("resolution_type"), data.get("priority", "Medium"),
              data.get("status", "Gap"), data.get("decision_rationale"), data.get("module")))
        
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "gap_id": auto_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============== DASHBOARD STATS API ==============

@app.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    """Dashboard icin istatistikler - proje bazli filtreleme destekli"""
    project_id = request.args.get('project_id')
    try:
        conn = get_db_connection()
        
        if project_id:
            # Proje seçiliyse sadece o projenin verileri
            total_sessions = conn.execute('SELECT COUNT(*) FROM analysis_sessions WHERE project_id = ?', (project_id,)).fetchone()[0]
            total_gaps = conn.execute('''
                SELECT COUNT(*) FROM fitgap f
                JOIN analysis_sessions s ON f.session_id = s.id
                WHERE s.project_id = ?
            ''', (project_id,)).fetchone()[0]
            total_questions = conn.execute('''
                SELECT COUNT(*) FROM questions q
                JOIN analysis_sessions s ON q.session_id = s.id
                WHERE s.project_id = ?
            ''', (project_id,)).fetchone()[0]
            
            # Recent activities for this project
            recent_activities = conn.execute('''
                SELECT * FROM analysis_sessions 
                WHERE project_id = ? 
                ORDER BY created_at DESC LIMIT 5
            ''', (project_id,)).fetchall()
            
            # Project info
            project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
            project_name = project['project_name'] if project else 'Unknown'
            project_status = project['status'] if project else 'Unknown'
        else:
            # Proje seçili değilse genel istatistikler
            total_sessions = conn.execute('SELECT COUNT(*) FROM analysis_sessions').fetchone()[0]
            total_gaps = conn.execute('SELECT COUNT(*) FROM fitgap').fetchone()[0]
            total_questions = conn.execute('SELECT COUNT(*) FROM questions').fetchone()[0]
            recent_activities = []
            project_name = 'All Projects'
            project_status = '-'
        
        # Genel sayılar (her zaman)
        total_projects = conn.execute('SELECT COUNT(*) FROM projects').fetchone()[0]
        total_requirements = conn.execute('SELECT COUNT(*) FROM requirements').fetchone()[0]
        
        conn.close()
        
        return jsonify({
            "total_projects": total_projects,
            "total_requirements": total_requirements,
            "total_sessions": total_sessions,
            "total_gaps": total_gaps,
            "total_questions": total_questions,
            "project_name": project_name,
            "project_status": project_status,
            "recent_activities": [dict(row) for row in recent_activities]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    # ============== FS/TS DOCUMENTS API ==============

@app.route('/api/documents', methods=['GET'])
def get_documents():
    """FS/TS dokümanlari listele"""
    project_id = request.args.get('project_id')
    requirement_id = request.args.get('requirement_id')
    try:
        conn = get_db_connection()
        if requirement_id:
            docs = conn.execute('''
                SELECT d.*, r.code as requirement_code, r.title as requirement_title
                FROM fs_ts_documents d
                JOIN requirements r ON d.requirement_id = r.id
                WHERE d.requirement_id = ?
                ORDER BY d.created_at DESC
            ''', (requirement_id,)).fetchall()
        elif project_id:
            docs = conn.execute('''
                SELECT d.*, r.code as requirement_code, r.title as requirement_title
                FROM fs_ts_documents d
                JOIN requirements r ON d.requirement_id = r.id
                WHERE r.project_id = ?
                ORDER BY d.created_at DESC
            ''', (project_id,)).fetchall()
        else:
            docs = conn.execute('''
                SELECT d.*, r.code as requirement_code, r.title as requirement_title
                FROM fs_ts_documents d
                JOIN requirements r ON d.requirement_id = r.id
                ORDER BY d.created_at DESC
            ''').fetchall()
        conn.close()
        return jsonify([dict(row) for row in docs])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/documents', methods=['POST'])
def add_document():
    """Yeni FS/TS dokümanı ekle"""
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO fs_ts_documents (requirement_id, document_type, version, content, template_used, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (data['requirement_id'], data['document_type'], data.get('version', '1.0'), 
              data.get('content', ''), data.get('template_used'), data.get('status', 'Draft')))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/documents/<int:doc_id>', methods=['GET'])
def get_document_detail(doc_id):
    """Tek bir doküman detayı"""
    try:
        conn = get_db_connection()
        doc = conn.execute('''
            SELECT d.*, r.code as requirement_code, r.title as requirement_title
            FROM fs_ts_documents d
            JOIN requirements r ON d.requirement_id = r.id
            WHERE d.id = ?
        ''', (doc_id,)).fetchone()
        conn.close()
        if doc:
            return jsonify(dict(doc))
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/api/documents/<int:doc_id>', methods=['PUT'])
def update_document(doc_id):
    """Doküman güncelle"""
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute('''
            UPDATE fs_ts_documents 
            SET content = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (data.get('content', ''), doc_id))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    # ============== TEST CASES API ==============

@app.route('/api/testcases', methods=['GET'])
def get_testcases():
    """Test case'leri listele"""
    project_id = request.args.get('project_id')
    fs_ts_id = request.args.get('fs_ts_id')
    try:
        conn = get_db_connection()
        if fs_ts_id:
            cases = conn.execute('''
                SELECT tc.*, d.document_type, r.code as requirement_code
                FROM test_cases tc
                JOIN fs_ts_documents d ON tc.fs_ts_id = d.id
                JOIN requirements r ON d.requirement_id = r.id
                WHERE tc.fs_ts_id = ?
                ORDER BY tc.created_at DESC
            ''', (fs_ts_id,)).fetchall()
        elif project_id:
            cases = conn.execute('''
                SELECT tc.*, d.document_type, r.code as requirement_code
                FROM test_cases tc
                JOIN fs_ts_documents d ON tc.fs_ts_id = d.id
                JOIN requirements r ON d.requirement_id = r.id
                WHERE r.project_id = ?
                ORDER BY tc.created_at DESC
            ''', (project_id,)).fetchall()
        else:
            cases = conn.execute('''
                SELECT tc.*, d.document_type, r.code as requirement_code
                FROM test_cases tc
                JOIN fs_ts_documents d ON tc.fs_ts_id = d.id
                JOIN requirements r ON d.requirement_id = r.id
                ORDER BY tc.created_at DESC
            ''').fetchall()
        conn.close()
        return jsonify([dict(row) for row in cases])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/testcases', methods=['POST'])
def add_testcase():
    """Yeni test case ekle"""
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO test_cases (fs_ts_id, test_case_id, test_scenario, test_type, preconditions, test_steps, expected_result, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (data['fs_ts_id'], data['test_case_id'], data.get('test_scenario'), data.get('test_type', 'Unit'),
              data.get('preconditions'), data.get('test_steps'), data.get('expected_result'), data.get('status', 'Not Started')))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/testcases/<int:tc_id>', methods=['PUT'])
def update_testcase(tc_id):
    """Test case güncelle"""
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute('''
            UPDATE test_cases 
            SET status = ?, executed_by = ?, executed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (data.get('status'), data.get('executed_by'), tc_id))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    # ============== AI SERVICES API (Mock) ==============
import time
import random

@app.route('/api/ai/generate-fs', methods=['POST'])
def generate_fs_content():
    """AI ile Functional Spec içeriği üret (Mock)"""
    try:
        data = request.json
        requirement_code = data.get('requirement_code', 'REQ-001')
        requirement_title = data.get('requirement_title', 'Requirement')
        module = data.get('module', 'MM')
        
        # Simüle edilmiş gecikme (gerçekçilik için)
        time.sleep(1)
        
        # Mock FS içeriği
        content = f"""# Functional Specification
## {requirement_code} - {requirement_title}

### 1. Document Information
- **Module:** {module}
- **Author:** AI Co-Pilot
- **Version:** 1.0
- **Status:** Draft

### 2. Business Requirements
This functional specification describes the business requirements for {requirement_title}.

#### 2.1 Business Context
The business process requires implementation of {requirement_title} to support daily operations in the {module} module.

#### 2.2 Scope
- In Scope: Core functionality for {requirement_title}
- Out of Scope: Integration with external systems (Phase 2)

### 3. Functional Requirements

#### 3.1 Process Flow
1. User initiates the process via transaction
2. System validates input data
3. Business logic is executed
4. Results are displayed/stored

#### 3.2 Business Rules
- Rule 1: All mandatory fields must be filled
- Rule 2: Authorization check required
- Rule 3: Document number range must be configured

### 4. Data Requirements
| Field | Type | Length | Required |
|-------|------|--------|----------|
| Document No | CHAR | 10 | Yes |
| Description | CHAR | 40 | Yes |
| Status | CHAR | 1 | Yes |

### 5. Authorization
- Authorization Object: Z_{module}_AUTH
- Required Activities: Create, Change, Display

### 6. Testing Requirements
- Unit testing required
- Integration testing with related processes
- UAT sign-off needed

---
*Generated by AI Co-Pilot*
"""
        return jsonify({
            "status": "success",
            "content": content,
            "tokens_used": random.randint(500, 1500)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/generate-ts', methods=['POST'])
def generate_ts_content():
    """AI ile Technical Spec içeriği üret (Mock)"""
    try:
        data = request.json
        requirement_code = data.get('requirement_code', 'REQ-001')
        requirement_title = data.get('requirement_title', 'Requirement')
        module = data.get('module', 'MM')
        
        time.sleep(1)
        
        # Mock TS içeriği
        content = f"""# Technical Specification
## {requirement_code} - {requirement_title}

### 1. Technical Overview
- **Development Type:** Enhancement
- **Package:** Z{module}_CUSTOM
- **Transport:** To be assigned

### 2. Development Objects

#### 2.1 Custom Tables
```
Table: Z{module}_CUSTOM_DATA
Fields:
  - MANDT (Client)
  - DOCNR (Document Number) - Key
  - BUKRS (Company Code)
  - ERDAT (Created Date)
  - ERNAM (Created By)
  - STATUS (Status)
```

#### 2.2 Function Modules
```abap
FUNCTION Z_{module}_PROCESS_DATA
  IMPORTING
    IV_DOCNR TYPE ZDOCNR
    IV_BUKRS TYPE BUKRS
  EXPORTING
    EV_STATUS TYPE ZSTATUS
  EXCEPTIONS
    NOT_FOUND
    INVALID_INPUT.
```

### 3. Implementation Details

#### 3.1 Main Logic (Pseudo-code)
```abap
METHOD process_document.
  " 1. Validate input
  IF iv_docnr IS INITIAL.
    RAISE EXCEPTION invalid_input.
  ENDIF.
  
  " 2. Read master data
  SELECT SINGLE * FROM z{module.lower()}_custom_data
    INTO @DATA(ls_data)
    WHERE docnr = @iv_docnr.
    
  " 3. Execute business logic
  CASE ls_data-status.
    WHEN '01'. " New
      perform_initial_processing( ).
    WHEN '02'. " In Process
      perform_update_processing( ).
  ENDCASE.
  
  " 4. Update status
  UPDATE z{module.lower()}_custom_data
    SET status = '03'
    WHERE docnr = iv_docnr.
ENDMETHOD.
```

### 4. Error Handling
| Error Code | Message | Action |
|------------|---------|--------|
| 001 | Document not found | Display error, return |
| 002 | Invalid status | Log warning, skip |
| 003 | Authorization failed | Raise exception |

### 5. Performance Considerations
- Use buffered tables where possible
- Implement parallel processing for mass operations
- Add appropriate indexes

### 6. Unit Test Cases
- Test Case 1: Valid document processing
- Test Case 2: Invalid input handling
- Test Case 3: Authorization check

---
*Generated by AI Co-Pilot*
"""
        return jsonify({
            "status": "success", 
            "content": content,
            "tokens_used": random.randint(800, 2000)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/analyze-gap', methods=['POST'])
def analyze_gap():
    """AI ile Gap analizi yap (Mock)"""
    try:
        data = request.json
        gap_description = data.get('description', '')
        
        time.sleep(0.5)
        
        # Mock analiz sonucu
        solutions = [
            {
                "type": "Configuration",
                "description": "This requirement can potentially be met with standard SAP configuration.",
                "effort": "Low (2-3 days)",
                "recommendation": "Review IMG settings and test with standard functionality first."
            },
            {
                "type": "Enhancement",
                "description": "A BAdI or User Exit implementation may be needed.",
                "effort": "Medium (5-8 days)", 
                "recommendation": "Check available enhancement spots in the relevant transaction."
            },
            {
                "type": "Custom Development",
                "description": "Full custom development (Report/Interface/Form) required.",
                "effort": "High (10-15 days)",
                "recommendation": "Create detailed FS/TS before development begins."
            }
        ]
        
        selected = random.choice(solutions)
        
        return jsonify({
            "status": "success",
            "analysis": selected,
            "confidence": random.randint(70, 95)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ai/chat', methods=['POST'])
def ai_chat():
    """AI Chat endpoint (Mock)"""
    try:
        data = request.json
        message = data.get('message', '')
        context = data.get('context', '')
        
        time.sleep(0.5)
        
        # Mock yanıtlar
        responses = [
            f"Based on your question about '{message[:50]}...', I recommend reviewing the standard SAP functionality first. This approach typically reduces development effort by 40%.",
            f"Great question! For '{message[:30]}...', the best practice in SAP S/4HANA is to use Fiori apps where possible. This ensures future compatibility.",
            f"I've analyzed your request. The technical implementation for '{message[:30]}...' would require a custom enhancement. I can help you draft the technical specification.",
            f"Looking at '{message[:30]}...', this seems like a common requirement. SAP provides standard solutions through Business Add-Ins (BAdIs) that we can leverage.",
            f"For '{message[:30]}...', I suggest we break this down into smaller components. This will make testing and maintenance easier."
        ]
        
        return jsonify({
            "status": "success",
            "response": random.choice(responses),
            "suggestions": [
                "Generate Technical Spec",
                "Show similar requirements",
                "Estimate effort"
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    cat >> app.py << 'APIEOF'

# ============== ATTENDEES API ==============

@app.route('/api/attendees', methods=['GET'])
def get_attendees():
    session_id = request.args.get('session_id')
    try:
        conn = get_db_connection()
        if session_id:
            attendees = conn.execute('SELECT * FROM session_attendees WHERE session_id = ? ORDER BY name', (session_id,)).fetchall()
        else:
            attendees = conn.execute('SELECT * FROM session_attendees ORDER BY created_at DESC').fetchall()
        conn.close()
        return jsonify([dict(row) for row in attendees])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/attendees', methods=['POST'])
def add_attendee():
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO session_attendees (session_id, name, email, role, department, company, is_required, attendance_status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (data['session_id'], data['name'], data.get('email'), data.get('role'), 
              data.get('department'), data.get('company'), data.get('is_required', 1),
              data.get('attendance_status', 'Invited'), data.get('notes')))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/attendees/<int:id>', methods=['PUT'])
def update_attendee(id):
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute('UPDATE session_attendees SET attendance_status = ?, notes = ? WHERE id = ?',
            (data.get('attendance_status'), data.get('notes'), id))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/attendees/<int:id>', methods=['DELETE'])
def delete_attendee(id):
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM session_attendees WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============== AGENDA API ==============

@app.route('/api/agenda', methods=['GET'])
def get_agenda():
    session_id = request.args.get('session_id')
    try:
        conn = get_db_connection()
        if session_id:
            items = conn.execute('SELECT * FROM session_agenda WHERE session_id = ? ORDER BY item_order', (session_id,)).fetchall()
        else:
            items = conn.execute('SELECT * FROM session_agenda ORDER BY created_at DESC').fetchall()
        conn.close()
        return jsonify([dict(row) for row in items])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/agenda', methods=['POST'])
def add_agenda_item():
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO session_agenda (session_id, item_order, topic, description, duration_minutes, presenter, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (data['session_id'], data.get('item_order', 1), data['topic'], data.get('description'),
              data.get('duration_minutes', 30), data.get('presenter'), data.get('status', 'Planned'), data.get('notes')))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/agenda/<int:id>', methods=['DELETE'])
def delete_agenda_item(id):
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM session_agenda WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============== MEETING MINUTES API ==============

@app.route('/api/minutes', methods=['GET'])
def get_minutes():
    session_id = request.args.get('session_id')
    try:
        conn = get_db_connection()
        if session_id:
            minutes = conn.execute('SELECT * FROM meeting_minutes WHERE session_id = ? ORDER BY minute_order', (session_id,)).fetchall()
        else:
            minutes = conn.execute('SELECT * FROM meeting_minutes ORDER BY created_at DESC').fetchall()
        conn.close()
        return jsonify([dict(row) for row in minutes])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/minutes', methods=['POST'])
def add_minute():
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO meeting_minutes (session_id, minute_order, topic, discussion, key_points, recorded_by)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (data['session_id'], data.get('minute_order', 1), data.get('topic'), 
              data.get('discussion'), data.get('key_points'), data.get('recorded_by')))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/minutes/<int:id>', methods=['DELETE'])
def delete_minute(id):
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM meeting_minutes WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============== ACTION ITEMS API ==============

@app.route('/api/actions', methods=['GET'])
def get_actions():
    session_id = request.args.get('session_id')
    project_id = request.args.get('project_id')
    try:
        conn = get_db_connection()
        if session_id:
            actions = conn.execute('SELECT * FROM action_items WHERE session_id = ? ORDER BY due_date', (session_id,)).fetchall()
        elif project_id:
            actions = conn.execute('''
                SELECT a.* FROM action_items a
                JOIN analysis_sessions s ON a.session_id = s.id
                WHERE s.project_id = ? ORDER BY a.due_date
            ''', (project_id,)).fetchall()
        else:
            actions = conn.execute('SELECT * FROM action_items ORDER BY due_date').fetchall()
        conn.close()
        return jsonify([dict(row) for row in actions])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/actions", methods=["POST"])
def add_action():
    try:
        data = request.json
        session_id = data.get("session_id")
        conn = get_db_connection()
        
        # Session dan project_id al
        session = conn.execute("SELECT project_id FROM analysis_sessions WHERE id = ?", (session_id,)).fetchone()
        project_id = session["project_id"] if session else None
        
        # Otomatik ID uret
        auto_id = generate_auto_id(project_id, "A") if project_id else None
        
        conn.execute("""
            INSERT INTO action_items (session_id, action_id, title, description, assigned_to,
            assigned_email, due_date, priority, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (session_id, auto_id, data.get("title"), data.get("description"),
              data.get("assigned_to"), data.get("assigned_email"), data.get("due_date"),
              data.get("priority", "Medium"), data.get("status", "Open"), data.get("notes")))
        
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "action_id": auto_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/actions/<int:id>', methods=['PUT'])
def update_action(id):
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute('UPDATE action_items SET status = ?, completion_date = ?, notes = ? WHERE id = ?',
            (data.get('status'), data.get('completion_date'), data.get('notes'), id))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/actions/<int:id>', methods=['DELETE'])
def delete_action(id):
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM action_items WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============== DECISIONS API ==============

@app.route('/api/decisions', methods=['GET'])
def get_decisions():
    session_id = request.args.get('session_id')
    project_id = request.args.get('project_id')
    try:
        conn = get_db_connection()
        if session_id:
            decisions = conn.execute('SELECT * FROM decisions WHERE session_id = ? ORDER BY created_at DESC', (session_id,)).fetchall()
        elif project_id:
            decisions = conn.execute('SELECT * FROM decisions WHERE project_id = ? ORDER BY created_at DESC', (project_id,)).fetchall()
        else:
            decisions = conn.execute('SELECT * FROM decisions ORDER BY created_at DESC').fetchall()
        conn.close()
        return jsonify([dict(row) for row in decisions])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/decisions", methods=["POST"])
def add_decision():
    try:
        data = request.json
        session_id = data.get("session_id")
        project_id = data.get("project_id")
        conn = get_db_connection()
        
        # Eger project_id yoksa session dan al
        if not project_id and session_id:
            session = conn.execute("SELECT project_id FROM analysis_sessions WHERE id = ?", (session_id,)).fetchone()
            project_id = session["project_id"] if session else None
        
        # Otomatik ID uret
        auto_id = generate_auto_id(project_id, "D") if project_id else None
        
        conn.execute("""
            INSERT INTO decisions (session_id, project_id, decision_id, topic, description, options_considered,
            decision_made, rationale, decision_maker, decision_date, impact_areas, status, related_gap_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (session_id, project_id, auto_id, data.get("topic"), data.get("description"),
              data.get("options_considered"), data.get("decision_made"), data.get("rationale"),
              data.get("decision_maker"), data.get("decision_date"), data.get("impact_areas"),
              data.get("status", "Draft"), data.get("related_gap_id")))
        
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "decision_id": auto_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ============== RISKS & ISSUES API ==============

@app.route('/api/risks', methods=['GET'])
def get_risks():
    session_id = request.args.get('session_id')
    project_id = request.args.get('project_id')
    item_type = request.args.get('type')
    try:
        conn = get_db_connection()
        query = 'SELECT * FROM risks_issues WHERE 1=1'
        params = []
        if session_id:
            query += ' AND session_id = ?'
            params.append(session_id)
        if project_id:
            query += ' AND project_id = ?'
            params.append(project_id)
        if item_type:
            query += ' AND type = ?'
            params.append(item_type)
        query += ' ORDER BY risk_score DESC, created_at DESC'
        risks = conn.execute(query, params).fetchall()
        conn.close()
        return jsonify([dict(row) for row in risks])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/risks", methods=["POST"])
def add_risk():
    try:
        data = request.json
        session_id = data.get("session_id")
        project_id = data.get("project_id")
        item_type = data.get("type", "Risk")
        
        conn = get_db_connection()
        
        # Eger project_id yoksa session dan al
        if not project_id and session_id:
            session = conn.execute("SELECT project_id FROM analysis_sessions WHERE id = ?", (session_id,)).fetchone()
            project_id = session["project_id"] if session else None
        
        # Otomatik ID uret (R = Risk, I = Issue)
        id_prefix = "R" if item_type == "Risk" else "I"
        auto_id = generate_auto_id(project_id, id_prefix) if project_id else None
        
        # Risk score hesapla
        impact_map = {"High": 3, "Medium": 2, "Low": 1}
        prob_map = {"High": 3, "Medium": 2, "Low": 1}
        impact = data.get("impact", "Medium")
        probability = data.get("probability", "Medium")
        risk_score = impact_map.get(impact, 2) * prob_map.get(probability, 2)
        
        conn.execute("""
            INSERT INTO risks_issues (session_id, project_id, item_id, type, title, description, category,
            impact, probability, risk_score, mitigation_plan, contingency_plan, owner, owner_email, status,
            target_resolution_date, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (session_id, project_id, auto_id, item_type, data.get("title"), data.get("description"),
              data.get("category"), impact, probability, risk_score, data.get("mitigation_plan"),
              data.get("contingency_plan"), data.get("owner"), data.get("owner_email"),
              data.get("status", "Open"), data.get("target_resolution_date"), data.get("notes")))
        
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "item_id": auto_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============== ANALYSIS STATS API ==============

@app.route('/api/analysis/stats', methods=['GET'])
def get_analysis_stats():
    project_id = request.args.get('project_id')
    try:
        conn = get_db_connection()
        if project_id:
            total_sessions = conn.execute('SELECT COUNT(*) FROM analysis_sessions WHERE project_id = ?', (project_id,)).fetchone()[0]
            fit_count = conn.execute('''SELECT COUNT(*) FROM fitgap f JOIN analysis_sessions s ON f.session_id = s.id WHERE s.project_id = ? AND f.status = 'Fit' ''', (project_id,)).fetchone()[0]
            gap_count = conn.execute('''SELECT COUNT(*) FROM fitgap f JOIN analysis_sessions s ON f.session_id = s.id WHERE s.project_id = ? AND f.status != 'Fit' ''', (project_id,)).fetchone()[0]
            open_questions = conn.execute('''SELECT COUNT(*) FROM questions q JOIN analysis_sessions s ON q.session_id = s.id WHERE s.project_id = ?''', (project_id,)).fetchone()[0]
            open_actions = conn.execute('''SELECT COUNT(*) FROM action_items a JOIN analysis_sessions s ON a.session_id = s.id WHERE s.project_id = ? AND a.status = 'Open' ''', (project_id,)).fetchone()[0]
            high_risks = conn.execute("SELECT COUNT(*) FROM risks_issues WHERE project_id = ? AND risk_score >= 6", (project_id,)).fetchone()[0]
        else:
            total_sessions = fit_count = gap_count = open_questions = open_actions = high_risks = 0
        conn.close()
        return jsonify({
            "total_sessions": total_sessions,
            "fit_count": fit_count,
            "gap_count": gap_count,
            "open_questions": open_questions,
            "open_actions": open_actions,
            "high_risks": high_risks
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============== SINGLE RECORD APIs ==============

@app.route('/api/questions/<int:id>', methods=['GET'])
def get_question_by_id(id):
    try:
        conn = get_db_connection()
        question = conn.execute('SELECT * FROM questions WHERE id = ?', (id,)).fetchone()
        conn.close()
        if question:
            return jsonify(dict(question))
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/questions/<int:id>', methods=['PUT'])
def update_question(id):
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute('''UPDATE questions SET 
            question_text = ?, answer_text = ?, status = ?, assigned_to = ?, due_date = ?
            WHERE id = ?''',
            (data.get('question_text'), data.get('answer_text'), data.get('status'),
             data.get('assigned_to'), data.get('due_date'), id))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/fitgap/<int:id>', methods=['GET'])
def get_fitgap_by_id(id):
    try:
        conn = get_db_connection()
        gap = conn.execute('SELECT * FROM fitgap WHERE id = ?', (id,)).fetchone()
        conn.close()
        if gap:
            return jsonify(dict(gap))
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/fitgap/<int:id>', methods=['PUT'])
def update_fitgap(id):
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute("""UPDATE fitgap SET 
            status = ?, priority = ?, module = ?, requirement_description = ?, 
            sap_standard_solution = ?, decision_rationale = ?,
            related_decision_id = ?, related_wricef_id = ?
            WHERE id = ?""",
            (data.get("status"), data.get("priority"), data.get("module"), data.get("requirement_description"),
             data.get("sap_standard_solution"), data.get("decision_rationale"),
             data.get("related_decision_id"), data.get("related_wricef_id"), id))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/actions/<int:id>', methods=['GET'])
def get_action_by_id(id):
    try:
        conn = get_db_connection()
        action = conn.execute('SELECT * FROM action_items WHERE id = ?', (id,)).fetchone()
        conn.close()
        if action:
            return jsonify(dict(action))
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/actions/<int:id>/full', methods=['PUT'])
def update_action_full(id):
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute('''UPDATE action_items SET 
            title = ?, description = ?, assigned_to = ?, due_date = ?, priority = ?, status = ?
            WHERE id = ?''',
            (data.get('title'), data.get('description'), data.get('assigned_to'),
             data.get('due_date'), data.get('priority'), data.get('status'), id))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    app.run(host="0.0.0.0", port=8080, debug=True)

# ============== DECISION SINGLE RECORD APIs ==============

@app.route('/api/decisions/<int:id>', methods=['GET'])
def get_decision_by_id(id):
    try:
        conn = get_db_connection()
        decision = conn.execute('SELECT * FROM decisions WHERE id = ?', (id,)).fetchone()
        conn.close()
        if decision:
            return jsonify(dict(decision))
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/decisions/<int:id>', methods=['PUT'])
def update_decision(id):
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute('''UPDATE decisions SET 
            status = ?, decision_maker = ?, topic = ?, options_considered = ?,
            decision_made = ?, rationale = ?, impact_areas = ?
            WHERE id = ?''',
            (data.get('status'), data.get('decision_maker'), data.get('topic'),
             data.get('options_considered'), data.get('decision_made'),
             data.get('rationale'), data.get('impact_areas'), id))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============== RISK SINGLE RECORD APIs ==============

@app.route('/api/risks/<int:id>', methods=['GET'])
def get_risk_by_id(id):
    try:
        conn = get_db_connection()
        risk = conn.execute('SELECT * FROM risks_issues WHERE id = ?', (id,)).fetchone()
        conn.close()
        if risk:
            return jsonify(dict(risk))
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/risks/<int:id>', methods=['PUT'])
def update_risk(id):
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute("""UPDATE risks_issues SET
            title = ?, description = ?, category = ?, impact = ?, probability = ?,
            mitigation_plan = ?, contingency_plan = ?, owner = ?, status = ?,
            scenario_id = ?, related_gap_id = ?, related_wricef_id = ?
            WHERE id = ?""",
            (data.get('title'), data.get('description'), data.get('category'),
             data.get('impact'), data.get('probability'), data.get('mitigation_plan'),
             data.get('contingency_plan'), data.get('owner'), data.get('status'),
             data.get('scenario_id'), data.get('related_gap_id'), data.get('related_wricef_id'), id))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============== SCENARIOS API ==============

@app.route('/api/scenarios', methods=['GET'])
def get_scenarios():
    project_id = request.args.get('project_id')
    try:
        query = Scenario.query
        if project_id:
            query = query.filter(Scenario.project_id == project_id)
        scenarios = query.order_by(Scenario.created_at.desc()).all()
        return jsonify([scenario.to_dict() for scenario in scenarios])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/scenarios', methods=['POST'])
def add_scenario():
    try:
        data = request.json
        project_id = data.get('project_id')
        auto_id = generate_auto_id(project_id, "S") if project_id else None
        scenario = Scenario(
            code=auto_id,
            project_id=project_id,
            name=data.get('name'),
            description=data.get('description'),
            process_area=data.get('process_area'),
            priority=data.get('priority', 'Medium'),
            status=data.get('status', 'Draft'),
            tags=data.get('tags'),
            is_composite=bool(data.get('is_composite', False)),
            included_scenario_ids=data.get('included_scenario_ids')
        )
        db.session.add(scenario)
        db.session.commit()
        return jsonify({"status": "success", "scenario_id": auto_id, "id": scenario.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/scenarios/<int:id>', methods=['GET'])
def get_scenario_by_id(id):
    try:
        scenario = Scenario.query.get(id)
        if scenario:
            return jsonify(scenario.to_dict())
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/scenarios/<int:id>', methods=['PUT'])
def update_scenario(id):
    try:
        data = request.json
        scenario = Scenario.query.get(id)
        if not scenario:
            return jsonify({"error": "Not found"}), 404
        scenario.name = data.get('name', scenario.name)
        scenario.description = data.get('description', scenario.description)
        scenario.process_area = data.get('process_area', scenario.process_area)
        scenario.priority = data.get('priority', scenario.priority)
        scenario.status = data.get('status', scenario.status)
        scenario.tags = data.get('tags', scenario.tags)
        if 'is_composite' in data:
            scenario.is_composite = bool(data.get('is_composite'))
        scenario.included_scenario_ids = data.get('included_scenario_ids', scenario.included_scenario_ids)
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/scenarios/<int:id>', methods=['DELETE'])
def delete_scenario(id):
    try:
        deleted = Scenario.query.filter(Scenario.id == id).delete()
        if deleted == 0:
            return jsonify({"error": "Not found"}), 404
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500



# ============== ANALYSES API (Epic A) ==============

@app.route('/api/scenarios/<int:scenario_id>/analyses', methods=['GET'])
def get_analyses_by_scenario(scenario_id):
    """List all analyses for a scenario (through analysis_sessions)"""
    try:
        conn = get_db_connection()
        rows = conn.execute("""
            SELECT DISTINCT a.id, a.session_id, a.analysis_type, a.title, a.content, a.status, a.created_at
            FROM analyses a
            INNER JOIN analysis_sessions s ON a.session_id = s.id
            WHERE s.scenario_id = ?
            ORDER BY a.created_at DESC
        """, (scenario_id,)).fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/scenarios/<int:scenario_id>/analyses', methods=['POST'])
def create_analysis(scenario_id):
    """Create a new analysis for a scenario (via a session)"""
    try:
        data = request.json
        title = data.get('title')
        if not title:
            return jsonify({"error": "title required"}), 400

        scenario = Scenario.query.get(scenario_id)
        if not scenario:
            return jsonify({"error": "Scenario not found"}), 404

        session_id = data.get('session_id')
        conn = get_db_connection()
        if session_id:
            session = conn.execute(
                "SELECT id FROM analysis_sessions WHERE id = ? AND scenario_id = ?",
                (session_id, scenario_id)
            ).fetchone()
            if not session:
                conn.close()
                return jsonify({"error": "Session not found for this scenario"}), 404
        else:
            row = conn.execute(
                "SELECT id FROM analysis_sessions WHERE scenario_id = ? ORDER BY created_at DESC LIMIT 1",
                (scenario_id,)
            ).fetchone()
            if row:
                session_id = row["id"]
            else:
                session_name = data.get('session_name') or f"Auto Session - {title}"
                cursor = conn.execute(
                    "INSERT INTO analysis_sessions (project_id, session_name, status, scenario_id) VALUES (?, ?, ?, ?)",
                    (scenario.project_id, session_name, 'Planned', scenario_id)
                )
                conn.commit()
                session_id = cursor.lastrowid
        conn.close()

        analysis = Analysis(
            session_id=session_id,
            title=title,
            analysis_type=data.get('analysis_type'),
            content=data.get('content', data.get('description')),
            status=data.get('status', 'Draft')
        )
        db.session.add(analysis)
        db.session.commit()
        return jsonify({"status": "success", "id": analysis.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route('/api/analyses/<int:id>', methods=['GET'])
def get_analysis_detail(id):
    """Get a single analysis detail"""
    try:
        analysis = Analysis.query.get(id)
        if analysis:
            return jsonify(analysis.to_dict())
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/analyses/<int:id>', methods=['PUT'])
def update_analysis(id):
    """Update an analysis"""
    try:
        data = request.json
        analysis = Analysis.query.get(id)
        if not analysis:
            return jsonify({"error": "Not found"}), 404
        
        analysis.title = data.get('title', analysis.title)
        analysis.analysis_type = data.get('analysis_type', analysis.analysis_type)
        if 'content' in data:
            analysis.content = data['content']
        elif 'description' in data:
            analysis.content = data['description']
        analysis.status = data.get('status', analysis.status)
        
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route('/api/analyses/<int:id>', methods=['DELETE'])
def delete_analysis(id):
    """Delete an analysis"""
    try:
        deleted = Analysis.query.filter(Analysis.id == id).delete()
        if deleted == 0:
            return jsonify({"error": "Not found"}), 404
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ============== WRICEF CRUD APIs ==============

@app.route('/api/wricef', methods=['GET'])
def get_wricefs():
    try:
        project_id = request.args.get('project_id')
        conn = get_db_connection()
        if project_id:
            rows = conn.execute('SELECT * FROM wricef WHERE project_id = ? ORDER BY id DESC', (project_id,)).fetchall()
        else:
            rows = conn.execute('SELECT * FROM wricef ORDER BY id DESC').fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/wricef', methods=['POST'])
def create_wricef():
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.execute("""INSERT INTO wricef 
            (wricef_id, project_id, type, name, description, complexity, estimated_effort, priority, status, assigned_to, related_gap_id, related_decision_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (data.get('wricef_id'), data.get('project_id'), data.get('type'), data.get('name'),
             data.get('description'), data.get('complexity', 'Medium'), data.get('estimated_effort'),
             data.get('priority', 'Medium'), data.get('status', 'Identified'), data.get('assigned_to'),
             data.get('related_gap_id'), data.get('related_decision_id')))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return jsonify({"status": "success", "id": new_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/wricef/<int:id>', methods=['GET'])
def get_wricef_by_id(id):
    try:
        conn = get_db_connection()
        row = conn.execute('SELECT * FROM wricef WHERE id = ?', (id,)).fetchone()
        conn.close()
        if row:
            return jsonify(dict(row))
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/wricef/<int:id>', methods=['PUT'])
def update_wricef(id):
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute("""UPDATE wricef SET
            wricef_id = ?, type = ?, name = ?, description = ?, complexity = ?,
            estimated_effort = ?, priority = ?, status = ?, assigned_to = ?,
            related_gap_id = ?, related_decision_id = ?
            WHERE id = ?""",
            (data.get('wricef_id'), data.get('type'), data.get('name'), data.get('description'),
             data.get('complexity'), data.get('estimated_effort'), data.get('priority'),
             data.get('status'), data.get('assigned_to'), data.get('related_gap_id'),
             data.get('related_decision_id'), id))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/wricef/<int:id>', methods=['DELETE'])
def delete_wricef(id):
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM wricef WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============== DECISION UPDATE API (with links) ==============

@app.route('/api/decisions/<int:id>/full', methods=['PUT'])
def update_decision_full(id):
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute("""UPDATE decisions SET
            topic = ?, description = ?, options_considered = ?, decision_made = ?,
            rationale = ?, decision_maker = ?, status = ?,
            related_gap_id = ?, related_wricef_id = ?, scenario_id = ?
            WHERE id = ?""",
            (data.get('topic'), data.get('description'), data.get('options_considered'),
             data.get('decision_made'), data.get('rationale'), data.get('decision_maker'),
             data.get('status'), data.get('related_gap_id'), data.get('related_wricef_id'),
             data.get('scenario_id'), id))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============== NEW REQUIREMENTS API (Phase 2.4 Group A) ==============
@app.route('/api/new_requirements', methods=['GET'])
def get_new_requirements():
    project_id = request.args.get('project_id')
    session_id = request.args.get('session_id')
    try:
        query = Requirement.query
        if session_id:
            query = query.filter(Requirement.session_id == session_id)
        elif project_id:
            query = query.filter(Requirement.project_id == project_id)
        requirements = query.order_by(Requirement.created_at.desc()).all()
        return jsonify([requirement.to_dict() for requirement in requirements])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/new_requirements', methods=['POST'])
def add_new_requirement():
    try:
        data = request.json
        requirement = Requirement(
            session_id=data.get('session_id'),
            project_id=data.get('project_id'),
            gap_id=data.get('gap_id'),
            analysis_id=data.get('analysis_id'),
            code=data.get('code'),
            title=data['title'],
            description=data.get('description'),
            module=data.get('module'),
            fit_type=data.get('fit_type'),
            classification=data.get('classification', 'Gap'),
            priority=data.get('priority', 'Medium'),
            acceptance_criteria=data.get('acceptance_criteria'),
            status=data.get('status', 'Draft')
        )
        db.session.add(requirement)
        db.session.commit()
        return jsonify({"status": "success", "id": requirement.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/new_requirements/<int:req_id>', methods=['GET'])
def get_new_requirement_detail(req_id):
    try:
        requirement = Requirement.query.get(req_id)
        if requirement:
            return jsonify(requirement.to_dict())
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/new_requirements/<int:req_id>', methods=['PUT'])
def update_new_requirement(req_id):
    try:
        data = request.json
        requirement = Requirement.query.get(req_id)
        if not requirement:
            return jsonify({"error": "Not found"}), 404
        requirement.title = data.get('title', requirement.title)
        requirement.description = data.get('description', requirement.description)
        requirement.classification = data.get('classification', requirement.classification)
        requirement.priority = data.get('priority', requirement.priority)
        requirement.status = data.get('status', requirement.status)
        requirement.acceptance_criteria = data.get('acceptance_criteria', requirement.acceptance_criteria)
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route('/api/new-requirements/<int:req_id>/convert', methods=['POST'])
def convert_requirement(req_id):
    try:
        requirement = Requirement.query.get(req_id)
        if not requirement:
            return jsonify({"error": "Not found"}), 404

        if requirement.conversion_status and requirement.conversion_status.lower() == 'converted':
            return jsonify({"error": "Already converted"}), 400

        classification = (requirement.classification or '').strip()
        conversion_type = None
        created_item = None

        if classification == 'Fit':
            created_item = ConfigItem(
                title=requirement.title,
                config_type=requirement.module or 'standard',
                description=requirement.description,
                status='planned',
                project_id=requirement.project_id,
                requirement_id=requirement.id
            )
            conversion_type = 'config'
        elif classification in ('Gap', 'PartialFit', 'Partial Fit'):
            created_item = WricefItem(
                title=requirement.title,
                wricef_type='E',
                description=requirement.description,
                status='identified',
                module=requirement.module,
                project_id=requirement.project_id,
                requirement_id=requirement.id
            )
            conversion_type = 'wricef'
        else:
            return jsonify({"error": "Invalid classification for conversion"}), 400

        db.session.add(created_item)
        db.session.flush()

        requirement.conversion_status = 'converted'
        requirement.conversion_type = conversion_type
        requirement.conversion_id = created_item.id
        requirement.converted_item_type = conversion_type
        requirement.converted_item_id = created_item.id
        requirement.converted_at = datetime.utcnow()

        db.session.commit()
        return jsonify({
            "message": "Converted successfully",
            "conversion_type": conversion_type,
            "created_item_id": created_item.id
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# ============== WRICEF ITEMS API (Phase 3.6 ORM) ==============
@app.route('/api/wricef_items', methods=['GET'])
def get_wricef_items():
    project_id = request.args.get('project_id')
    requirement_id = request.args.get('requirement_id')
    try:
        query = WricefItem.query
        if requirement_id:
            query = query.filter(WricefItem.requirement_id == requirement_id)
        elif project_id:
            query = query.filter(WricefItem.project_id == project_id)
        items = query.order_by(WricefItem.created_at.desc()).all()
        return jsonify([item.to_dict() for item in items])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/wricef_items', methods=['POST'])
def add_wricef_item():
    try:
        data = request.json
        item = WricefItem(
            project_id=data.get('project_id'),
            requirement_id=data.get('requirement_id'),
            code=data.get('code'),
            title=data.get('title'),
            description=data.get('description'),
            wricef_type=data.get('wricef_type'),
            module=data.get('module'),
            complexity=data.get('complexity'),
            effort_days=data.get('effort_days'),
            status=data.get('status', 'Draft'),
            owner=data.get('owner'),
            fs_content=data.get('fs_content'),
            ts_content=data.get('ts_content'),
            unit_test_steps=data.get('unit_test_steps'),
            fs_link=data.get('fs_link'),
            ts_link=data.get('ts_link')
        )
        db.session.add(item)
        db.session.commit()
        return jsonify({"status": "success", "id": item.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/wricef_items/<int:item_id>', methods=['GET'])
def get_wricef_item_detail(item_id):
    try:
        item = WricefItem.query.get(item_id)
        if item:
            return jsonify(item.to_dict())
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/wricef_items/<int:item_id>', methods=['PUT'])
def update_wricef_item(item_id):
    try:
        data = request.json
        item = WricefItem.query.get(item_id)
        if not item:
            return jsonify({"error": "Not found"}), 404
        item.title = data.get('title', item.title)
        item.description = data.get('description', item.description)
        item.wricef_type = data.get('wricef_type', item.wricef_type)
        item.module = data.get('module', item.module)
        item.complexity = data.get('complexity', item.complexity)
        item.effort_days = data.get('effort_days', item.effort_days)
        item.status = data.get('status', item.status)
        item.owner = data.get('owner', item.owner)
        if 'fs_content' in data:
            item.fs_content = data['fs_content']
        if 'ts_content' in data:
            item.ts_content = data['ts_content']
        if 'unit_test_steps' in data:
            item.unit_test_steps = data['unit_test_steps']
        if 'fs_link' in data:
            item.fs_link = data['fs_link']
        if 'ts_link' in data:
            item.ts_link = data['ts_link']
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/wricef_items/<int:item_id>', methods=['DELETE'])
def delete_wricef_item(item_id):
    try:
        deleted = WricefItem.query.filter(WricefItem.id == item_id).delete()
        if deleted == 0:
            return jsonify({"error": "Not found"}), 404
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route('/api/wricef-items/<int:item_id>/convert-to-test', methods=['POST'])
def convert_wricef_to_test(item_id):
    try:
        item = WricefItem.query.get(item_id)
        if not item:
            return jsonify({"error": "Not found"}), 404

        code = f"TST-{int(datetime.utcnow().timestamp())}"
        test_case = TestCase(
            project_id=item.project_id,
            code=code,
            test_type='unit',
            title=f"Unit Test: {item.title}",
            source_type='wricef',
            source_id=item.id,
            status='not_started',
            steps=item.unit_test_steps
        )
        db.session.add(test_case)
        db.session.commit()
        return jsonify({"status": "success", "id": test_case.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# ============== CONFIG ITEMS API (Phase 3.7 ORM) ==============
@app.route('/api/config_items', methods=['GET'])
def get_config_items():
    project_id = request.args.get('project_id')
    requirement_id = request.args.get('requirement_id')
    try:
        query = ConfigItem.query
        if requirement_id:
            query = query.filter(ConfigItem.requirement_id == requirement_id)
        elif project_id:
            query = query.filter(ConfigItem.project_id == project_id)
        items = query.order_by(ConfigItem.created_at.desc()).all()
        return jsonify([item.to_dict() for item in items])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/config_items', methods=['POST'])
def add_config_item():
    try:
        data = request.json
        item = ConfigItem(
            project_id=data.get('project_id'),
            requirement_id=data.get('requirement_id'),
            code=data.get('code'),
            title=data.get('title'),
            description=data.get('description'),
            config_type=data.get('config_type'),
            module=data.get('module'),
            status=data.get('status', 'Draft'),
            owner=data.get('owner'),
            config_details=data.get('config_details'),
            unit_test_steps=data.get('unit_test_steps')
        )
        db.session.add(item)
        db.session.commit()
        return jsonify({"status": "success", "id": item.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/config_items/<int:item_id>', methods=['GET'])
def get_config_item_detail(item_id):
    try:
        item = ConfigItem.query.get(item_id)
        if item:
            return jsonify(item.to_dict())
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/config_items/<int:item_id>', methods=['PUT'])
def update_config_item(item_id):
    try:
        data = request.json
        item = ConfigItem.query.get(item_id)
        if not item:
            return jsonify({"error": "Not found"}), 404
        item.title = data.get('title', item.title)
        item.description = data.get('description', item.description)
        item.config_type = data.get('config_type', item.config_type)
        item.module = data.get('module', item.module)
        item.status = data.get('status', item.status)
        item.owner = data.get('owner', item.owner)
        if 'config_details' in data:
            item.config_details = data['config_details']
        if 'unit_test_steps' in data:
            item.unit_test_steps = data['unit_test_steps']
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/config_items/<int:item_id>', methods=['DELETE'])
def delete_config_item(item_id):
    try:
        deleted = ConfigItem.query.filter(ConfigItem.id == item_id).delete()
        if deleted == 0:
            return jsonify({"error": "Not found"}), 404
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route('/api/config-items/<int:item_id>/convert-to-test', methods=['POST'])
def convert_config_to_test(item_id):
    try:
        item = ConfigItem.query.get(item_id)
        if not item:
            return jsonify({"error": "Not found"}), 404

        code = f"TST-{int(datetime.utcnow().timestamp())}"
        test_case = TestCase(
            project_id=item.project_id,
            code=code,
            test_type='unit',
            title=f"Unit Test: {item.title}",
            source_type='config',
            source_id=item.id,
            status='not_started',
            steps=item.unit_test_steps
        )
        db.session.add(test_case)
        db.session.commit()
        return jsonify({"status": "success", "id": test_case.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# ============== TEST MANAGEMENT API (Phase 3.8 ORM) ==============
@app.route('/api/test_management', methods=['GET'])
def get_test_management():
    project_id = request.args.get('project_id')
    try:
        query = TestCase.query
        if project_id:
            query = query.filter(TestCase.project_id == project_id)
        items = query.order_by(TestCase.created_at.desc()).all()
        return jsonify([item.to_dict() for item in items])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/test_management', methods=['POST'])
def add_test_management():
    try:
        data = request.json
        item = TestCase(
            project_id=data.get('project_id'),
            code=data.get('code'),
            test_type=data.get('test_type'),
            title=data.get('title'),
            description=data.get('description'),
            status=data.get('status', 'Draft'),
            owner=data.get('owner'),
            source_type=data.get('source_type'),
            source_id=data.get('source_id'),
            steps=data.get('steps')
        )
        db.session.add(item)
        db.session.commit()
        return jsonify({"status": "success", "id": item.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/test_management/<int:item_id>', methods=['GET'])
def get_test_management_detail(item_id):
    try:
        item = TestCase.query.get(item_id)
        if item:
            return jsonify(item.to_dict())
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/test_management/<int:item_id>', methods=['PUT'])
def update_test_management(item_id):
    try:
        data = request.json
        item = TestCase.query.get(item_id)
        if not item:
            return jsonify({"error": "Not found"}), 404
        item.title = data.get('title', item.title)
        item.description = data.get('description', item.description)
        item.status = data.get('status', item.status)
        item.owner = data.get('owner', item.owner)
        if 'test_type' in data:
            item.test_type = data['test_type']
        if 'source_type' in data:
            item.source_type = data['source_type']
        if 'source_id' in data:
            item.source_id = data['source_id']
        if 'steps' in data:
            item.steps = data['steps']
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/test_management/<int:item_id>', methods=['DELETE'])
def delete_test_management(item_id):
    try:
        deleted = TestCase.query.filter(TestCase.id == item_id).delete()
        if deleted == 0:
            return jsonify({"error": "Not found"}), 404
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
