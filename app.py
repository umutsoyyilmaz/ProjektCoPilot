from flask import Flask, render_template, jsonify, request
import sqlite3
import os
import re
import logging
from contextlib import contextmanager
from datetime import datetime

# Import SQLAlchemy models
from models import (
    db, Project, Scenario, Analysis, Requirement,
    WricefItem, ConfigItem, TestCase, TestCycle, TestExecution, Defect,
    AIInteractionLog, AIEmbedding,
    generate_code,
    PROJECT_STATUSES, PROJECT_PHASES, SCENARIO_LEVELS, CLASSIFICATIONS,
    PRIORITIES, CONVERSION_STATUSES, WRICEF_TYPES, SAP_MODULES,
    DEV_STATUSES, TEST_TYPES, TEST_CASE_STATUSES
)

app = Flask(__name__)

# SQLAlchemy Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project_copilot.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False  # Set True for debugging

# Initialize SQLAlchemy
db.init_app(app)

# logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)
def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), 'project_copilot.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # wrap connection so we can rewrite "SELECT *" to explicit columns
    class DBConnProxy:
        def __init__(self, conn):
            self._conn = conn

        def __getattr__(self, name):
            return getattr(self._conn, name)

        def _cols_for_table(self, table_name):
            cols_map = {
                'requirements': 'id, project_id, code, title, module, complexity, status, ai_status, effort_days, summary',
                'projects': 'id, project_code, project_name, customer_name, start_date, end_date, status, modules, environment, description, customer_industry, customer_country, customer_contact, customer_email, deployment_type, implementation_approach, sap_modules, golive_planned, golive_actual, project_manager, solution_architect, functional_lead, technical_lead, total_budget, current_phase, completion_percent, created_at',
                'analysis_sessions': 'id, project_id, scenario_id, session_name, session_code, module, process_name, session_date, facilitator, status, notes, created_at',
                'questions': 'id, session_id, question_id, question_text, category, question_order, is_mandatory, answer_text, answered_by, status, created_at',
                'answers': 'id, question_id, answer_text, answered_by, answered_at, confidence_score',
                'fitgap': 'id, session_id, project_id, gap_id, process_name, gap_description, impact_area, solution_type, risk_level, effort_estimate, priority, status, notes, created_at',
                'fs_ts_documents': 'id, requirement_id, document_type, version, content, template_used, status, approved_by, approved_at, file_path, sharepoint_url, created_at, updated_at',
                'test_cases': 'id, fs_ts_id, test_case_id, test_scenario, test_type, preconditions, test_steps, expected_result, status, environment, executed_by, executed_at, alm_reference, created_at',
                'audit_log': 'id, table_name, record_id, action, old_values, new_values, changed_by, changed_at',
                'scenarios': 'id, project_id, scenario_id, name, description, process_area, priority, status, is_composite, included_scenario_ids, tags, created_at',
                'session_attendees': 'id, session_id, name, role, department, email, status, created_at',
                'session_agenda': 'id, session_id, item_order, topic, description, duration_minutes, presenter, status, notes, created_at',
                'meeting_minutes': 'id, session_id, minute_order, topic, discussion, content, key_points, recorded_by, created_at',
                'action_items': 'id, session_id, project_id, action_id, title, description, assigned_to, due_date, priority, status, source, related_gap_id, created_at',
                'decisions': 'id, session_id, project_id, decision_id, topic, description, options_considered, decision_made, rationale, decision_maker, decision_date, impact_areas, status, related_gap_id, created_at',
                'risks_issues': 'id, session_id, project_id, item_id, title, description, item_type, type, probability, impact_level, risk_score, status, owner, mitigation, contingency, created_at',
                'analyses': 'id, session_id, analysis_type, title, content, status, created_at',
                'scenario_analyses': 'id, scenario_id, code, title, description, owner, status, created_at, updated_at',
                'new_requirements': 'id, session_id, project_id, gap_id, code, analysis_id, title, description, module, fit_type, classification, priority, status, conversion_status, converted_item_type, converted_item_id, converted_at, converted_by, acceptance_criteria, created_at',
                'wricef_items': 'id, project_id, requirement_id, scenario_id, code, title, description, wricef_type, module, complexity, effort_days, status, owner, fs_content, fs_link, ts_content, ts_link, unit_test_steps, created_at, updated_at',
                'config_items': 'id, project_id, requirement_id, scenario_id, code, title, description, config_type, module, status, owner, config_details, unit_test_steps, created_at, updated_at',
                'wricef': 'id, code, wricef_id, title, wricef_type, module, status',
                'test_management': 'id, project_id, code, test_type, title, description, status, owner, source_type, source_id, steps, created_at, updated_at'
            }
            return cols_map.get(table_name, None)

        def execute(self, sql, params=()):
            try:
                # rewrite SELECT * FROM table_name to explicit cols when known
                m = re.search(r"SELECT\s+\*\s+FROM\s+([A-Za-z0-9_]+)", sql, re.IGNORECASE)
                if m:
                    table = m.group(1)
                    cols = self._cols_for_table(table)
                    if cols:
                        sql = re.sub(r"SELECT\s+\*\s+FROM\s+%s" % table, f"SELECT {cols} FROM {table}", sql, flags=re.IGNORECASE)
                return self._conn.execute(sql, params)
            except Exception:
                # fallback to original execute for unexpected cases
                return self._conn.execute(sql, params)

    return DBConnProxy(conn)


@contextmanager
def db_conn():
    conn = get_db_connection()
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass


def require_fields(data, fields):
    missing = [f for f in fields if not data or f not in data]
    return missing

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
        "ANL": ("scenario_analyses", "code"),
        "REQ": ("new_requirements", "code"),
        "WR": ("wricef", "wricef_id"),
        "C": ("configs", "config_id"),
        "TEST": ("test_management", "code"),
    }
    
    if item_type not in table_map:
        conn.close()
        return None
    
    table, id_column = table_map[item_type]

    # safety: ensure identifiers are simple (prevent injection via mapping tampering)
    ident_re = re.compile(r'^[A-Za-z0-9_]+$')
    if not ident_re.match(table) or not ident_re.match(id_column):
        conn.close()
        return None
    
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
        with db_conn() as conn:
            # avoid SELECT * where possible; here keep simple columns for the view
            requirements = conn.execute('SELECT id, project_id, code, title, status FROM requirements').fetchall()
            recent_activities = conn.execute(
                'SELECT id, project_id, code, title, status FROM requirements ORDER BY id DESC LIMIT 5'
            ).fetchall()
        return render_template('index.html', requirements=requirements, recent_activities=recent_activities)
    except Exception as e:
        logger.exception('Failed to render index')
        return "Veritabanı hatası oluştu.", 500
@app.route('/api/requirements', methods=['GET'])
def get_requirements():
    """Tum requirementlari listele"""
    project_id = request.args.get('project_id')
    try:
        with db_conn() as conn:
            if project_id:
                requirements = conn.execute('SELECT id, project_id, code, title, status FROM requirements WHERE project_id = ? ORDER BY id DESC', (project_id,)).fetchall()
            else:
                requirements = conn.execute('SELECT id, project_id, code, title, status FROM requirements ORDER BY id DESC').fetchall()
        return jsonify([dict(row) for row in requirements])
    except Exception as e:
        logger.exception('get_requirements failed')
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/requirements', methods=['POST'])
def add_requirement():
    try:
        data = request.json
        missing = require_fields(data, ['code', 'title'])
        if missing:
            return jsonify({'error': 'missing_fields', 'fields': missing}), 400
        with db_conn() as conn:
            conn.execute('''
                INSERT INTO requirements (project_id, code, title, module, complexity, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (data.get('project_id'), data['code'], data['title'], data.get('module'), data.get('complexity'), 'Draft'))
            conn.commit()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logger.exception('add_requirement failed')
        return jsonify({"status": "error", "message": "Internal server error"}), 500

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
    """Tum projeleri listele (ORM)"""
    try:
        projects = Project.query.order_by(Project.created_at.desc()).all()
        return jsonify([p.to_dict() for p in projects])
    except Exception as e:
        logger.exception('get_projects failed')
        return jsonify({"error": str(e)}), 500

@app.route("/api/projects", methods=["POST"])
def add_project():
    """Create new project (ORM)"""
    try:
        data = request.json
        missing = require_fields(data, ['project_code', 'project_name'])
        if missing:
            return jsonify({'error': 'missing_fields', 'fields': missing}), 400

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
            start_date=data.get("start_date"),
            golive_planned=data.get("golive_planned"),
            golive_actual=data.get("golive_actual"),
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
        return jsonify({"status": "success", "id": project.id}), 201
    except Exception as e:
        db.session.rollback()
        logger.exception('add_project failed')
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/projects/<int:project_id>', methods=['GET'])
def get_project_detail(project_id):
    """Tek bir projenin detayini getir (ORM)"""
    try:
        project = Project.query.get_or_404(project_id)
        return jsonify(project.to_dict())
    except Exception as e:
        logger.exception('get_project_detail failed')
        return jsonify({"error": str(e)}), 404

@app.route("/api/projects/<int:id>", methods=["PUT"])
def update_project(id):
    """Update project (ORM)"""
    try:
        data = request.json
        project = Project.query.get_or_404(id)
        
        # Update fields
        if 'project_code' in data: project.code = data['project_code']
        if 'project_name' in data: project.name = data['project_name']
        if 'description' in data: project.description = data['description']
        if 'status' in data: project.status = data['status']
        if 'customer_name' in data: project.customer_name = data['customer_name']
        if 'customer_industry' in data: project.customer_industry = data['customer_industry']
        if 'customer_country' in data: project.customer_country = data['customer_country']
        if 'customer_contact' in data: project.customer_contact = data['customer_contact']
        if 'customer_email' in data: project.customer_email = data['customer_email']
        if 'deployment_type' in data: project.deployment_type = data['deployment_type']
        if 'implementation_approach' in data: project.implementation_approach = data['implementation_approach']
        if 'sap_modules' in data: project.sap_modules = data['sap_modules']
        if 'start_date' in data: project.start_date = data['start_date']
        if 'golive_planned' in data: project.golive_planned = data['golive_planned']
        if 'golive_actual' in data: project.golive_actual = data['golive_actual']
        if 'project_manager' in data: project.project_manager = data['project_manager']
        if 'solution_architect' in data: project.solution_architect = data['solution_architect']
        if 'functional_lead' in data: project.functional_lead = data['functional_lead']
        if 'technical_lead' in data: project.technical_lead = data['technical_lead']
        if 'total_budget' in data: project.total_budget = data['total_budget']
        if 'current_phase' in data: project.phase = data['current_phase']
        if 'completion_percent' in data: project.completion_percent = data['completion_percent']
        
        project.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        db.session.rollback()
        logger.exception('update_project failed')
        return jsonify({"error": str(e)}), 500

@app.route("/api/projects/<int:id>", methods=["DELETE"])
def delete_project(id):
    """Delete project (ORM)"""
    try:
        project = Project.query.get_or_404(id)
        db.session.delete(project)
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        db.session.rollback()
        logger.exception('delete_project failed')
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
        missing = require_fields(data, ['project_id', 'session_name'])
        if missing:
            return jsonify({'error': 'missing_fields', 'fields': missing}), 400
        with db_conn() as conn:
            conn.execute('''
                INSERT INTO analysis_sessions (project_id, scenario_id, session_name, module, process_name, facilitator, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (data['project_id'], data.get('scenario_id'), data['session_name'], data.get('module'), 
                  data.get('process_name'), data.get('facilitator'), data.get('status', 'Planned'), data.get('notes')))
            conn.commit()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logger.exception('add_session failed')
        return jsonify({"error": "Internal server error"}), 500

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
        missing = require_fields(data, ['session_id', 'question_text'])
        if missing:
            return jsonify({'error': 'missing_fields', 'fields': missing}), 400
        with db_conn() as conn:
            # Session dan project_id al
            session = conn.execute("SELECT project_id FROM analysis_sessions WHERE id = ?", (session_id,)).fetchone()
            project_id = session["project_id"] if session else None
            auto_id = generate_auto_id(project_id, "Q") if project_id else None
            cursor = conn.execute("""
                INSERT INTO questions (session_id, question_id, question_text, answer_text, status, assigned_to, due_date, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime("now"))
            """, (session_id, auto_id, data.get("question_text"), data.get("answer_text"),
                  data.get("status", "Open"), data.get("assigned_to"), data.get("due_date")))
            conn.commit()
        return jsonify({"success": True, "id": cursor.lastrowid, "question_id": auto_id}), 201
    except Exception as e:
        logger.exception('add_question failed')
        return jsonify({"error": "Internal server error"}), 500
    
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

# ============== NEW REQUIREMENTS API ==============
@app.route('/api/new_requirements', methods=['GET'])
def get_new_requirements():
    """Get requirements with optional filtering by analysis_id, project_id, classification, or status"""
    project_id = request.args.get('project_id')
    session_id = request.args.get('session_id')
    analysis_id = request.args.get('analysis_id')
    classification = request.args.get('classification')
    status = request.args.get('status')
    
    try:
        with db_conn() as conn:
            query = 'SELECT * FROM new_requirements WHERE 1=1'
            params = []
            
            if analysis_id:
                query += ' AND analysis_id = ?'
                params.append(analysis_id)
            elif session_id:
                query += ' AND session_id = ?'
                params.append(session_id)
            elif project_id:
                query += ' AND project_id = ?'
                params.append(project_id)
            
            if classification:
                query += ' AND classification = ?'
                params.append(classification)
            
            if status:
                query += ' AND status = ?'
                params.append(status)
            
            query += ' ORDER BY created_at DESC'
            
            rows = conn.execute(query, params).fetchall()
            result = [dict(r) for r in rows]
            
            # Add analysis info for each requirement if analysis_id exists
            for req in result:
                if req.get('analysis_id'):
                    analysis = conn.execute(
                        'SELECT id, code, title FROM scenario_analyses WHERE id = ?',
                        (req['analysis_id'],)
                    ).fetchone()
                    if analysis:
                        req['analysis'] = dict(analysis)
            
            return jsonify(result)
    except Exception as e:
        logger.exception("Error fetching requirements")
        return jsonify({"error": "Failed to fetch requirements"}), 500

@app.route('/api/new_requirements', methods=['POST'])
def add_new_requirement():
    """Create a new requirement with auto-generated code and classification validation"""
    try:
        data = request.json
        
        # Validate required fields
        missing = require_fields(data, ['title', 'analysis_id'])
        if missing:
            return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
        
        # Validate classification
        classification = data.get('classification', 'Gap')
        valid_classifications = ['Fit', 'PartialFit', 'Gap']
        if classification not in valid_classifications:
            return jsonify({"error": f"Invalid classification. Must be one of: {', '.join(valid_classifications)}"}), 400
        
        analysis_id = data.get('analysis_id')
        
        with db_conn() as conn:
            # Validate analysis exists and get project_id
            analysis = conn.execute(
                'SELECT id, scenario_id FROM scenario_analyses WHERE id = ?',
                (analysis_id,)
            ).fetchone()
            
            if not analysis:
                return jsonify({"error": "Analysis not found"}), 404
            
            # Get project_id from scenario
            scenario = conn.execute(
                'SELECT project_id FROM scenarios WHERE id = ?',
                (analysis['scenario_id'],)
            ).fetchone()
            
            project_id = scenario['project_id'] if scenario else None
            
            # Generate auto code (REQ-001 format)
            auto_code = generate_auto_id(project_id, "REQ") if project_id else None
            
            cursor = conn.execute('''
                INSERT INTO new_requirements (
                    code, analysis_id, project_id, session_id, gap_id,
                    title, description, module, fit_type, classification,
                    priority, status, acceptance_criteria
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                auto_code,
                analysis_id,
                project_id,
                data.get('session_id'),
                data.get('gap_id'),
                data['title'],
                data.get('description'),
                data.get('module'),
                data.get('fit_type'),
                classification,
                data.get('priority', 'Medium'),
                data.get('status', 'Draft'),
                data.get('acceptance_criteria')
            ))
            conn.commit()
            new_id = cursor.lastrowid
            
            return jsonify({
                "status": "success",
                "id": new_id,
                "code": auto_code
            }), 201
    except Exception as e:
        logger.exception("Error creating requirement")
        return jsonify({"error": "Failed to create requirement"}), 500

@app.route('/api/new_requirements/<int:req_id>', methods=['GET'])
def get_new_requirement_detail(req_id):
    """Get requirement by ID with analysis and conversion details"""
    try:
        with db_conn() as conn:
            row = conn.execute('SELECT * FROM new_requirements WHERE id = ?', (req_id,)).fetchone()
            
            if not row:
                return jsonify({"error": "Requirement not found"}), 404
            
            result = dict(row)
            
            # Add analysis details
            if result.get('analysis_id'):
                analysis = conn.execute(
                    'SELECT * FROM scenario_analyses WHERE id = ?',
                    (result['analysis_id'],)
                ).fetchone()
                if analysis:
                    result['analysis'] = dict(analysis)
            
            # Add converted item details if converted
            if result.get('conversion_status') == 'converted' and result.get('converted_item_id'):
                item_type = result.get('converted_item_type')
                if item_type == 'WRICEF':
                    item = conn.execute(
                        'SELECT id, code, title, status FROM wricef_items WHERE id = ?',
                        (result['converted_item_id'],)
                    ).fetchone()
                    if item:
                        result['converted_item'] = dict(item)
                elif item_type == 'CONFIG':
                    item = conn.execute(
                        'SELECT id, code, title, status FROM config_items WHERE id = ?',
                        (result['converted_item_id'],)
                    ).fetchone()
                    if item:
                        result['converted_item'] = dict(item)
            
            return jsonify(result)
    except Exception as e:
        logger.exception(f"Error fetching requirement {req_id}")
        return jsonify({"error": "Failed to fetch requirement"}), 500

@app.route('/api/new_requirements/<int:req_id>', methods=['PUT'])
def update_new_requirement(req_id):
    """Update requirement with classification validation"""
    try:
        data = request.json
        
        # Validate classification if provided
        if 'classification' in data:
            valid_classifications = ['Fit', 'PartialFit', 'Gap']
            if data['classification'] not in valid_classifications:
                return jsonify({"error": f"Invalid classification. Must be one of: {', '.join(valid_classifications)}"}), 400
        
        with db_conn() as conn:
            # Check if requirement exists
            existing = conn.execute(
                'SELECT * FROM new_requirements WHERE id = ?',
                (req_id,)
            ).fetchone()
            
            if not existing:
                return jsonify({"error": "Requirement not found"}), 404
            
            # Check if already converted - prevent modification of certain fields
            if existing['conversion_status'] == 'converted':
                if 'classification' in data and data['classification'] != existing['classification']:
                    return jsonify({"error": "Cannot change classification of converted requirement"}), 400
            
            # Update fields
            conn.execute('''
                UPDATE new_requirements 
                SET title = ?, description = ?, module = ?, classification = ?, 
                    priority = ?, status = ?, acceptance_criteria = ?
                WHERE id = ?
            ''', (
                data.get('title', existing['title']),
                data.get('description', existing['description']),
                data.get('module', existing['module']),
                data.get('classification', existing['classification']),
                data.get('priority', existing['priority']),
                data.get('status', existing['status']),
                data.get('acceptance_criteria', existing['acceptance_criteria']),
                req_id
            ))
            conn.commit()
            
            return jsonify({"status": "success"})
    except Exception as e:
        logger.exception(f"Error updating requirement {req_id}")
        return jsonify({"error": "Failed to update requirement"}), 500

@app.route('/api/new_requirements/<int:req_id>', methods=['DELETE'])
def delete_new_requirement(req_id):
    """Delete requirement with conversion check"""
    try:
        with db_conn() as conn:
            # Check if requirement exists
            requirement = conn.execute(
                'SELECT * FROM new_requirements WHERE id = ?',
                (req_id,)
            ).fetchone()
            
            if not requirement:
                return jsonify({"error": "Requirement not found"}), 404
            
            # Check if already converted - prevent deletion
            if requirement['conversion_status'] == 'converted':
                return jsonify({
                    "error": f"Cannot delete converted requirement. It has been converted to {requirement['converted_item_type']} (ID: {requirement['converted_item_id']})"
                }), 400
            
            # Safe to delete
            conn.execute('DELETE FROM new_requirements WHERE id = ?', (req_id,))
            conn.commit()
            
            return jsonify({"status": "success"})
    except Exception as e:
        logger.exception(f"Error deleting requirement {req_id}")
        return jsonify({"error": "Failed to delete requirement"}), 500


# ============== REQUIREMENT CONVERSION API (Epic B) ==============

@app.route('/api/new_requirements/<int:req_id>/convert', methods=['POST'])
def convert_requirement(req_id):
    """Convert requirement to WRICEF or CONFIG item based on classification"""
    try:
        data = request.json or {}
        converted_by = data.get('converted_by', 'system')
        
        with db_conn() as conn:
            # Get requirement with analysis and scenario info
            requirement = conn.execute(
                'SELECT * FROM new_requirements WHERE id = ?',
                (req_id,)
            ).fetchone()
            
            if not requirement:
                return jsonify({"error": "Requirement not found"}), 404
            
            # Check if already converted
            if requirement['conversion_status'] == 'converted':
                return jsonify({
                    "error": f"Requirement already converted to {requirement['converted_item_type']} (ID: {requirement['converted_item_id']})"
                }), 400
            
            # Validate classification exists
            classification = requirement['classification']
            if not classification:
                return jsonify({"error": "Requirement must have a classification before conversion"}), 400
            
            # Get scenario_id from analysis
            scenario_id = None
            if requirement['analysis_id']:
                analysis = conn.execute(
                    'SELECT scenario_id FROM scenario_analyses WHERE id = ?',
                    (requirement['analysis_id'],)
                ).fetchone()
                if analysis:
                    scenario_id = analysis['scenario_id']
            
            project_id = requirement['project_id']
            
            # Determine conversion target based on classification
            if classification == 'Fit':
                # Convert to CONFIG
                auto_code = generate_auto_id(project_id, "C") if project_id else None
                
                cursor = conn.execute('''
                    INSERT INTO config_items (
                        project_id, requirement_id, scenario_id, code, title, description,
                        config_type, module, status, owner, config_details, unit_test_steps
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    project_id,
                    req_id,
                    scenario_id,
                    auto_code,
                    requirement['title'],
                    requirement['description'],
                    data.get('config_type', 'Standard'),
                    requirement['module'],
                    'Draft',
                    data.get('owner'),  # Owner from payload only
                    data.get('config_details', ''),
                    '[]'  # Empty unit test steps initially
                ))
                new_item_id = cursor.lastrowid
                item_type = 'CONFIG'
                
            elif classification in ['Gap', 'PartialFit']:
                # Convert to WRICEF
                auto_code = generate_auto_id(project_id, "WR") if project_id else None
                
                cursor = conn.execute('''
                    INSERT INTO wricef_items (
                        project_id, requirement_id, scenario_id, code, title, description,
                        wricef_type, module, complexity, effort_days, status, owner,
                        fs_content, ts_content, unit_test_steps
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    project_id,
                    req_id,
                    scenario_id,
                    auto_code,
                    requirement['title'],
                    requirement['description'],
                    data.get('wricef_type', 'Enhancement'),
                    requirement['module'],
                    data.get('complexity', 'Medium'),
                    data.get('effort_days', 0),
                    'Draft',
                    data.get('owner'),  # Owner from payload only
                    '',  # Empty FS content initially
                    '',  # Empty TS content initially
                    '[]'  # Empty unit test steps initially
                ))
                new_item_id = cursor.lastrowid
                item_type = 'WRICEF'
                
            else:
                return jsonify({
                    "error": f"Invalid classification '{classification}' for conversion. Must be Fit, Gap, or PartialFit."
                }), 400
            
            # Update requirement with conversion info
            conn.execute('''
                UPDATE new_requirements
                SET conversion_status = 'converted',
                    converted_item_type = ?,
                    converted_item_id = ?,
                    converted_at = CURRENT_TIMESTAMP,
                    converted_by = ?
                WHERE id = ?
            ''', (item_type, new_item_id, converted_by, req_id))
            
            conn.commit()
            
            return jsonify({
                "status": "success",
                "converted_to": item_type,
                "item_id": new_item_id,
                "item_code": auto_code,
                "message": f"Requirement successfully converted to {item_type}"
            }), 201
            
    except Exception as e:
        logger.exception(f"Error converting requirement {req_id}")
        return jsonify({"error": "Failed to convert requirement"}), 500


# ============== WRICEF ITEMS API ==============
@app.route('/api/wricef_items', methods=['GET'])
def get_wricef_items():
    project_id = request.args.get('project_id')
    requirement_id = request.args.get('requirement_id')
    try:
        conn = get_db_connection()
        if requirement_id:
            rows = conn.execute('SELECT * FROM wricef_items WHERE requirement_id = ? ORDER BY created_at DESC', (requirement_id,)).fetchall()
        elif project_id:
            rows = conn.execute('SELECT * FROM wricef_items WHERE project_id = ? ORDER BY created_at DESC', (project_id,)).fetchall()
        else:
            rows = conn.execute('SELECT * FROM wricef_items ORDER BY created_at DESC').fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/wricef_items', methods=['POST'])
def add_wricef_item():
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO wricef_items (project_id, requirement_id, code, title, description, wricef_type, module, complexity, effort_days, status, owner)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (data.get('project_id'), data.get('requirement_id'), data.get('code'), data['title'], data.get('description'), data.get('wricef_type'), data.get('module'), data.get('complexity'), data.get('effort_days'), data.get('status','Draft'), data.get('owner')))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/wricef_items/<int:item_id>', methods=['GET'])
def get_wricef_item_detail(item_id):
    try:
        conn = get_db_connection()
        row = conn.execute('SELECT * FROM wricef_items WHERE id = ?', (item_id,)).fetchone()
        conn.close()
        if row:
            return jsonify(dict(row))
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/wricef_items/<int:item_id>', methods=['PUT'])
def update_wricef_item(item_id):
    try:
        data = request.json
        conn = get_db_connection()
        
        # Build dynamic UPDATE query based on provided fields
        update_fields = []
        values = []
        
        for field in ['title', 'description', 'wricef_type', 'module', 'complexity', 'effort_days', 'status', 'owner', 'unit_test_steps']:
            if field in data:
                update_fields.append(f"{field} = ?")
                values.append(data[field])
        
        if not update_fields:
            conn.close()
            return jsonify({"status": "success"})
        
        values.append(item_id)
        query = f"UPDATE wricef_items SET {', '.join(update_fields)} WHERE id = ?"
        
        conn.execute(query, values)
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/wricef_items/<int:item_id>', methods=['DELETE'])
def delete_wricef_item(item_id):
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM wricef_items WHERE id = ?', (item_id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/wricef_items/<int:item_id>/convert-to-unit-test', methods=['POST'])
def convert_wricef_to_unit_test(item_id):
    """Convert WRICEF item to Unit Test in test_management"""
    try:
        data = request.json or {}
        
        with db_conn() as conn:
            # Get WRICEF item
            wricef = conn.execute(
                'SELECT * FROM wricef_items WHERE id = ?',
                (item_id,)
            ).fetchone()
            
            if not wricef:
                return jsonify({"error": "WRICEF item not found"}), 404
            
            project_id = wricef['project_id']
            
            # Generate auto-code for test
            auto_code = generate_auto_id(project_id, "TEST") if project_id else None
            
            # Parse unit_test_steps (JSON string) to copy to test steps
            import json
            try:
                unit_test_steps = json.loads(wricef['unit_test_steps']) if wricef['unit_test_steps'] else []
                steps_json = json.dumps(unit_test_steps)
            except:
                steps_json = '[]'
            
            # Create unit test in test_management
            cursor = conn.execute('''
                INSERT INTO test_management (
                    project_id, code, test_type, title, description,
                    status, owner, source_type, source_id, steps
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                project_id,
                auto_code,
                'Unit',
                f"Unit Test: {wricef['title']}",
                wricef['description'],
                data.get('status', 'Draft'),
                data.get('owner', wricef['owner']),
                'WRICEF',
                item_id,
                steps_json
            ))
            test_id = cursor.lastrowid
            
            conn.commit()
            
            return jsonify({
                "status": "success",
                "test_id": test_id,
                "test_code": auto_code,
                "message": "WRICEF item successfully converted to Unit Test"
            }), 201
            
    except Exception as e:
        logger.exception(f"Error converting WRICEF {item_id} to unit test")
        return jsonify({"error": "Failed to convert to unit test"}), 500

# ============== CONFIG ITEMS API ==============
@app.route('/api/config_items', methods=['GET'])
def get_config_items():
    project_id = request.args.get('project_id')
    requirement_id = request.args.get('requirement_id')
    try:
        conn = get_db_connection()
        if requirement_id:
            rows = conn.execute('SELECT * FROM config_items WHERE requirement_id = ? ORDER BY created_at DESC', (requirement_id,)).fetchall()
        elif project_id:
            rows = conn.execute('SELECT * FROM config_items WHERE project_id = ? ORDER BY created_at DESC', (project_id,)).fetchall()
        else:
            rows = conn.execute('SELECT * FROM config_items ORDER BY created_at DESC').fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/config_items', methods=['POST'])
def add_config_item():
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO config_items (project_id, requirement_id, code, title, description, config_type, module, status, owner, config_details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (data.get('project_id'), data.get('requirement_id'), data.get('code'), data['title'], data.get('description'), data.get('config_type'), data.get('module'), data.get('status','Draft'), data.get('owner'), data.get('config_details')))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/config_items/<int:item_id>', methods=['GET'])
def get_config_item_detail(item_id):
    try:
        conn = get_db_connection()
        row = conn.execute('SELECT * FROM config_items WHERE id = ?', (item_id,)).fetchone()
        conn.close()
        if row:
            return jsonify(dict(row))
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/config_items/<int:item_id>', methods=['PUT'])
def update_config_item(item_id):
    try:
        data = request.json
        conn = get_db_connection()
        
        # Build dynamic UPDATE query based on provided fields
        update_fields = []
        values = []
        
        for field in ['title', 'description', 'config_type', 'module', 'status', 'owner', 'config_details', 'unit_test_steps']:
            if field in data:
                update_fields.append(f"{field} = ?")
                values.append(data[field])
        
        if not update_fields:
            conn.close()
            return jsonify({"status": "success"})
        
        values.append(item_id)
        query = f"UPDATE config_items SET {', '.join(update_fields)} WHERE id = ?"
        
        conn.execute(query, values)
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/config_items/<int:item_id>', methods=['DELETE'])
def delete_config_item(item_id):
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM config_items WHERE id = ?', (item_id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/config_items/<int:item_id>/convert-to-unit-test', methods=['POST'])
def convert_config_to_unit_test(item_id):
    """Convert CONFIG item to Unit Test in test_management"""
    try:
        data = request.json or {}
        
        with db_conn() as conn:
            # Get CONFIG item
            config = conn.execute(
                'SELECT * FROM config_items WHERE id = ?',
                (item_id,)
            ).fetchone()
            
            if not config:
                return jsonify({"error": "CONFIG item not found"}), 404
            
            project_id = config['project_id']
            
            # Generate auto-code for test
            auto_code = generate_auto_id(project_id, "TEST") if project_id else None
            
            # Parse unit_test_steps (JSON string) to copy to test steps
            import json
            try:
                unit_test_steps = json.loads(config['unit_test_steps']) if config['unit_test_steps'] else []
                steps_json = json.dumps(unit_test_steps)
            except:
                steps_json = '[]'
            
            # Create unit test in test_management
            cursor = conn.execute('''
                INSERT INTO test_management (
                    project_id, code, test_type, title, description,
                    status, owner, source_type, source_id, steps
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                project_id,
                auto_code,
                'Unit',
                f"Unit Test: {config['title']}",
                config['description'],
                data.get('status', 'Draft'),
                data.get('owner', config['owner']),
                'CONFIG',
                item_id,
                steps_json
            ))
            test_id = cursor.lastrowid
            
            conn.commit()
            
            return jsonify({
                "status": "success",
                "test_id": test_id,
                "test_code": auto_code,
                "message": "CONFIG item successfully converted to Unit Test"
            }), 201
            
    except Exception as e:
        logger.exception(f"Error converting CONFIG {item_id} to unit test")
        return jsonify({"error": "Failed to convert to unit test"}), 500

# ============== TEST MANAGEMENT API ==============
@app.route('/api/test_management', methods=['GET'])
def get_test_management():
    """Get test cases with optional filtering by project_id and test_type"""
    project_id = request.args.get('project_id')
    test_type = request.args.get('test_type')  # Unit, SIT, UAT, String, Sprint, PerformanceLoad, Regression
    
    try:
        with db_conn() as conn:
            # Build query with filters
            query = 'SELECT * FROM test_management WHERE 1=1'
            params = []
            
            if project_id:
                query += ' AND project_id = ?'
                params.append(project_id)
            
            if test_type:
                query += ' AND test_type = ?'
                params.append(test_type)
            
            query += ' ORDER BY created_at DESC'
            
            rows = conn.execute(query, params).fetchall()
            return jsonify([dict(r) for r in rows])
    except Exception as e:
        logger.exception("Error getting test management items")
        return jsonify({"error": str(e)}), 500

@app.route('/api/test_management', methods=['POST'])
def add_test_management():
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO test_management (project_id, code, test_type, title, description, status, owner, source_type, source_id, steps)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (data.get('project_id'), data.get('code'), data.get('test_type'), data['title'], data.get('description'), data.get('status','Draft'), data.get('owner'), data.get('source_type'), data.get('source_id'), data.get('steps','[]')))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/test_management/<int:item_id>', methods=['GET'])
def get_test_management_detail(item_id):
    try:
        conn = get_db_connection()
        row = conn.execute('SELECT * FROM test_management WHERE id = ?', (item_id,)).fetchone()
        conn.close()
        if row:
            return jsonify(dict(row))
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/test_management/<int:item_id>', methods=['PUT'])
def update_test_management(item_id):
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute('''
            UPDATE test_management SET title = ?, description = ?, status = ?, owner = ?, steps = ?
            WHERE id = ?
        ''', (data.get('title'), data.get('description'), data.get('status'), data.get('owner'), data.get('steps'), item_id))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/test_management/<int:item_id>', methods=['DELETE'])
def delete_test_management(item_id):
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM test_management WHERE id = ?', (item_id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
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
    """Get scenarios with optional filtering and composite scenario expansion"""
    project_id = request.args.get('project_id')
    status = request.args.get('status')
    include_composite_details = request.args.get('expand_composite', 'false').lower() == 'true'
    
    try:
        with db_conn() as conn:
            query = 'SELECT * FROM scenarios WHERE 1=1'
            params = []
            
            if project_id:
                query += ' AND project_id = ?'
                params.append(project_id)
            
            if status:
                query += ' AND status = ?'
                params.append(status)
            
            query += ' ORDER BY created_at DESC'
            
            scenarios = conn.execute(query, params).fetchall()
            result = [dict(s) for s in scenarios]
            
            # Expand composite scenarios if requested
            if include_composite_details:
                for scenario in result:
                    if scenario.get('is_composite') == 1 and scenario.get('included_scenario_ids'):
                        # Parse included scenario IDs
                        included_ids = scenario['included_scenario_ids'].split(',')
                        placeholders = ','.join(['?'] * len(included_ids))
                        included_scenarios = conn.execute(
                            f'SELECT id, scenario_id, name, status FROM scenarios WHERE id IN ({placeholders})',
                            included_ids
                        ).fetchall()
                        scenario['included_scenarios'] = [dict(s) for s in included_scenarios]
            
            return jsonify(result)
    except Exception as e:
        logger.exception("Error fetching scenarios")
        return jsonify({"error": "Failed to fetch scenarios"}), 500

@app.route('/api/scenarios', methods=['POST'])
def add_scenario():
    """Create a new scenario with composite support and validation"""
    try:
        data = request.json
        
        # Validate required fields
        missing = require_fields(data, ['project_id', 'name'])
        if missing:
            return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
        
        project_id = data.get('project_id')
        is_composite = data.get('is_composite', 0)
        included_scenario_ids = data.get('included_scenario_ids', [])
        tags = data.get('tags', [])
        
        # Validate composite scenario
        if is_composite and not included_scenario_ids:
            return jsonify({"error": "Composite scenarios must include at least one scenario"}), 400
        
        # Convert arrays to comma-separated strings
        included_ids_str = ','.join(map(str, included_scenario_ids)) if included_scenario_ids else None
        tags_str = ','.join(tags) if tags else None
        
        with db_conn() as conn:
            # Generate auto ID
            auto_id = generate_auto_id(project_id, "S") if project_id else None
            
            # Validate included scenarios exist (if composite)
            if is_composite and included_scenario_ids:
                placeholders = ','.join(['?'] * len(included_scenario_ids))
                existing = conn.execute(
                    f'SELECT COUNT(*) FROM scenarios WHERE id IN ({placeholders}) AND project_id = ?',
                    included_scenario_ids + [project_id]
                ).fetchone()[0]
                
                if existing != len(included_scenario_ids):
                    return jsonify({"error": "Some included scenarios do not exist or belong to different project"}), 400
            
            cursor = conn.execute('''
                INSERT INTO scenarios (
                    scenario_id, project_id, name, description, process_area, priority, status,
                    is_composite, included_scenario_ids, tags
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                auto_id, project_id, data.get('name'), data.get('description'),
                data.get('process_area'), data.get('priority', 'Medium'), data.get('status', 'Draft'),
                is_composite, included_ids_str, tags_str
            ))
            conn.commit()
            new_id = cursor.lastrowid
            
            return jsonify({
                "status": "success",
                "id": new_id,
                "scenario_id": auto_id
            }), 201
    except Exception as e:
        logger.exception("Error creating scenario")
        return jsonify({"error": "Failed to create scenario"}), 500

@app.route('/api/scenarios/<int:id>', methods=['GET'])
def get_scenario_by_id(id):
    """Get scenario by ID with expanded composite scenario details"""
    try:
        with db_conn() as conn:
            scenario = conn.execute('SELECT * FROM scenarios WHERE id = ?', (id,)).fetchone()
            
            if not scenario:
                return jsonify({"error": "Scenario not found"}), 404
            
            result = dict(scenario)
            
            # Expand composite scenario details
            if result.get('is_composite') == 1 and result.get('included_scenario_ids'):
                included_ids = result['included_scenario_ids'].split(',')
                placeholders = ','.join(['?'] * len(included_ids))
                included_scenarios = conn.execute(
                    f'SELECT * FROM scenarios WHERE id IN ({placeholders})',
                    included_ids
                ).fetchall()
                result['included_scenarios'] = [dict(s) for s in included_scenarios]
            
            # Get related analyses count
            analyses_count = conn.execute(
                'SELECT COUNT(*) FROM scenario_analyses WHERE scenario_id = ?',
                (id,)
            ).fetchone()[0]
            result['analyses_count'] = analyses_count
            
            # Parse tags if present
            if result.get('tags'):
                result['tags'] = result['tags'].split(',')
            
            return jsonify(result)
    except Exception as e:
        logger.exception(f"Error fetching scenario {id}")
        return jsonify({"error": "Failed to fetch scenario"}), 500

@app.route('/api/scenarios/<int:id>', methods=['PUT'])
def update_scenario(id):
    """Update scenario including composite scenario relationships"""
    try:
        data = request.json
        
        with db_conn() as conn:
            # Check if scenario exists
            existing = conn.execute('SELECT * FROM scenarios WHERE id = ?', (id,)).fetchone()
            if not existing:
                return jsonify({"error": "Scenario not found"}), 404
            
            # Handle composite scenario updates
            is_composite = data.get('is_composite', existing['is_composite'])
            included_scenario_ids = data.get('included_scenario_ids')
            tags = data.get('tags')
            
            # Validate composite scenario
            if is_composite and included_scenario_ids is not None:
                if not included_scenario_ids:
                    return jsonify({"error": "Composite scenarios must include at least one scenario"}), 400
                
                # Validate included scenarios exist and don't include self
                if id in included_scenario_ids:
                    return jsonify({"error": "Scenario cannot include itself"}), 400
                
                placeholders = ','.join(['?'] * len(included_scenario_ids))
                existing_count = conn.execute(
                    f'SELECT COUNT(*) FROM scenarios WHERE id IN ({placeholders}) AND project_id = ?',
                    included_scenario_ids + [existing['project_id']]
                ).fetchone()[0]
                
                if existing_count != len(included_scenario_ids):
                    return jsonify({"error": "Some included scenarios do not exist or belong to different project"}), 400
            
            # Convert arrays to strings
            included_ids_str = ','.join(map(str, included_scenario_ids)) if included_scenario_ids is not None else existing['included_scenario_ids']
            tags_str = ','.join(tags) if tags is not None else existing['tags']
            
            conn.execute('''
                UPDATE scenarios 
                SET name = ?, description = ?, process_area = ?, priority = ?, status = ?,
                    is_composite = ?, included_scenario_ids = ?, tags = ?
                WHERE id = ?
            ''', (
                data.get('name', existing['name']),
                data.get('description', existing['description']),
                data.get('process_area', existing['process_area']),
                data.get('priority', existing['priority']),
                data.get('status', existing['status']),
                is_composite,
                included_ids_str,
                tags_str,
                id
            ))
            conn.commit()
            
            return jsonify({"status": "success"})
    except Exception as e:
        logger.exception(f"Error updating scenario {id}")
        return jsonify({"error": "Failed to update scenario"}), 500

@app.route('/api/scenarios/<int:id>/create-test', methods=['POST'])
def create_test_from_scenario(id):
    """Create SIT/UAT/other test from scenario (with composite expansion support)"""
    try:
        data = request.json or {}
        test_type = data.get('test_type', 'SIT')  # SIT, UAT, String, Sprint, PerformanceLoad, Regression
        
        # Validate test_type
        valid_test_types = ['Unit', 'SIT', 'UAT', 'String', 'Sprint', 'PerformanceLoad', 'Regression']
        if test_type not in valid_test_types:
            return jsonify({
                "error": f"Invalid test_type. Must be one of: {', '.join(valid_test_types)}"
            }), 400
        
        with db_conn() as conn:
            # Get scenario
            scenario = conn.execute(
                'SELECT * FROM scenarios WHERE id = ?',
                (id,)
            ).fetchone()
            
            if not scenario:
                return jsonify({"error": "Scenario not found"}), 404
            
            project_id = scenario['project_id']
            
            # Generate auto-code for test
            auto_code = generate_auto_id(project_id, "TEST") if project_id else None
            
            # Build test title and description
            title = f"{test_type} Test: {scenario['name']}"
            description = scenario['description'] or ''
            
            # For composite scenarios (especially UAT), expand included scenarios
            scenario_details = {
                "main_scenario": scenario['name'],
                "is_composite": bool(scenario['is_composite'])
            }
            
            if scenario['is_composite'] and scenario['included_scenario_ids']:
                try:
                    import json
                    included_ids = json.loads(scenario['included_scenario_ids'])
                    included_scenarios = []
                    
                    for inc_id in included_ids:
                        inc_scenario = conn.execute(
                            'SELECT id, scenario_id, name FROM scenarios WHERE id = ?',
                            (inc_id,)
                        ).fetchone()
                        if inc_scenario:
                            included_scenarios.append({
                                "id": inc_scenario['id'],
                                "scenario_id": inc_scenario['scenario_id'],
                                "name": inc_scenario['name']
                            })
                    
                    scenario_details["included_scenarios"] = included_scenarios
                    
                    # Add included scenario names to description
                    if included_scenarios:
                        description += f"\n\nComposite Test Coverage:\n"
                        for inc in included_scenarios:
                            description += f"- {inc['name']}\n"
                except:
                    pass
            
            # Create test in test_management
            import json
            cursor = conn.execute('''
                INSERT INTO test_management (
                    project_id, code, test_type, title, description,
                    status, owner, source_type, source_id, steps
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                project_id,
                auto_code,
                test_type,
                title,
                description,
                data.get('status', 'Draft'),
                data.get('owner'),
                'SCENARIO',
                id,
                json.dumps(data.get('steps', []))
            ))
            test_id = cursor.lastrowid
            
            conn.commit()
            
            return jsonify({
                "status": "success",
                "test_id": test_id,
                "test_code": auto_code,
                "test_type": test_type,
                "scenario_details": scenario_details,
                "message": f"{test_type} test successfully created from scenario"
            }), 201
            
    except Exception as e:
        logger.exception(f"Error creating test from scenario {id}")
        return jsonify({"error": "Failed to create test from scenario"}), 500

@app.route('/api/scenarios/<int:id>', methods=['DELETE'])
def delete_scenario(id):
    """Delete scenario with cascade checks"""
    try:
        with db_conn() as conn:
            # Check if scenario exists
            scenario = conn.execute('SELECT * FROM scenarios WHERE id = ?', (id,)).fetchone()
            if not scenario:
                return jsonify({"error": "Scenario not found"}), 404
            
            # Check for related analyses
            analyses_count = conn.execute(
                'SELECT COUNT(*) FROM scenario_analyses WHERE scenario_id = ?',
                (id,)
            ).fetchone()[0]
            
            if analyses_count > 0:
                return jsonify({
                    "error": f"Cannot delete scenario with {analyses_count} related analyses. Delete analyses first."
                }), 400
            
            # Check if this scenario is included in composite scenarios
            composite_scenarios = conn.execute(
                "SELECT id, name FROM scenarios WHERE included_scenario_ids LIKE ?",
                (f'%{id}%',)
            ).fetchall()
            
            if composite_scenarios:
                scenario_names = [s['name'] for s in composite_scenarios]
                return jsonify({
                    "error": f"Scenario is included in composite scenarios: {', '.join(scenario_names)}. Remove from composite scenarios first."
                }), 400
            
            # Safe to delete
            conn.execute('DELETE FROM scenarios WHERE id = ?', (id,))
            conn.commit()
            
            return jsonify({"status": "success"})
    except Exception as e:
        logger.exception(f"Error deleting scenario {id}")
        return jsonify({"error": "Failed to delete scenario"}), 500




# ============== ANALYSIS MANAGEMENT APIs (Epic A2) ==============

@app.route('/api/analyses', methods=['GET'])
def get_analyses():
    """Get analyses with optional scenario filtering"""
    scenario_id = request.args.get('scenario_id')
    status = request.args.get('status')
    
    try:
        with db_conn() as conn:
            query = 'SELECT * FROM scenario_analyses WHERE 1=1'
            params = []
            
            if scenario_id:
                query += ' AND scenario_id = ?'
                params.append(scenario_id)
            
            if status:
                query += ' AND status = ?'
                params.append(status)
            
            query += ' ORDER BY created_at DESC'
            
            analyses = conn.execute(query, params).fetchall()
            result = [dict(a) for a in analyses]
            
            # Add scenario info for each analysis
            for analysis in result:
                scenario = conn.execute(
                    'SELECT id, scenario_id, name FROM scenarios WHERE id = ?',
                    (analysis['scenario_id'],)
                ).fetchone()
                if scenario:
                    analysis['scenario'] = dict(scenario)
            
            return jsonify(result)
    except Exception as e:
        logger.exception("Error fetching analyses")
        return jsonify({"error": "Failed to fetch analyses"}), 500

@app.route('/api/analyses', methods=['POST'])
def add_analysis():
    """Create a new analysis with auto-generated code"""
    try:
        data = request.json
        
        # Validate required fields
        missing = require_fields(data, ['scenario_id', 'title'])
        if missing:
            return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
        
        scenario_id = data.get('scenario_id')
        
        with db_conn() as conn:
            # Validate scenario exists
            scenario = conn.execute(
                'SELECT id, project_id FROM scenarios WHERE id = ?',
                (scenario_id,)
            ).fetchone()
            
            if not scenario:
                return jsonify({"error": "Scenario not found"}), 404
            
            # Generate auto code (ANL-001 format)
            project_id = scenario['project_id']
            auto_code = generate_auto_id(project_id, "ANL") if project_id else None
            
            cursor = conn.execute('''
                INSERT INTO scenario_analyses (
                    scenario_id, code, title, description, owner, status
                )
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                scenario_id,
                auto_code,
                data.get('title'),
                data.get('description'),
                data.get('owner'),
                data.get('status', 'Draft')
            ))
            conn.commit()
            new_id = cursor.lastrowid
            
            return jsonify({
                "status": "success",
                "id": new_id,
                "code": auto_code
            }), 201
    except Exception as e:
        logger.exception("Error creating analysis")
        return jsonify({"error": "Failed to create analysis"}), 500

@app.route('/api/analyses/<int:id>', methods=['GET'])
def get_analysis_by_id(id):
    """Get analysis by ID with scenario details"""
    try:
        with db_conn() as conn:
            analysis = conn.execute(
                'SELECT * FROM scenario_analyses WHERE id = ?',
                (id,)
            ).fetchone()
            
            if not analysis:
                return jsonify({"error": "Analysis not found"}), 404
            
            result = dict(analysis)
            
            # Add scenario details
            scenario = conn.execute(
                'SELECT * FROM scenarios WHERE id = ?',
                (result['scenario_id'],)
            ).fetchone()
            if scenario:
                result['scenario'] = dict(scenario)
            
            # Count related requirements
            req_count = conn.execute(
                'SELECT COUNT(*) FROM new_requirements WHERE analysis_id = ?',
                (id,)
            ).fetchone()[0]
            result['requirements_count'] = req_count
            
            return jsonify(result)
    except Exception as e:
        logger.exception(f"Error fetching analysis {id}")
        return jsonify({"error": "Failed to fetch analysis"}), 500

@app.route('/api/analyses/<int:id>', methods=['PUT'])
def update_analysis(id):
    """Update analysis"""
    try:
        data = request.json
        
        with db_conn() as conn:
            # Check if analysis exists
            existing = conn.execute(
                'SELECT * FROM scenario_analyses WHERE id = ?',
                (id,)
            ).fetchone()
            
            if not existing:
                return jsonify({"error": "Analysis not found"}), 404
            
            # Update timestamp
            conn.execute('''
                UPDATE scenario_analyses 
                SET title = ?, description = ?, owner = ?, status = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                data.get('title', existing['title']),
                data.get('description', existing['description']),
                data.get('owner', existing['owner']),
                data.get('status', existing['status']),
                id
            ))
            conn.commit()
            
            return jsonify({"status": "success"})
    except Exception as e:
        logger.exception(f"Error updating analysis {id}")
        return jsonify({"error": "Failed to update analysis"}), 500

@app.route('/api/analyses/<int:id>', methods=['DELETE'])
def delete_analysis(id):
    """Delete analysis with cascade checks"""
    try:
        with db_conn() as conn:
            # Check if analysis exists
            analysis = conn.execute(
                'SELECT * FROM scenario_analyses WHERE id = ?',
                (id,)
            ).fetchone()
            
            if not analysis:
                return jsonify({"error": "Analysis not found"}), 404
            
            # Check for related requirements
            req_count = conn.execute(
                'SELECT COUNT(*) FROM new_requirements WHERE analysis_id = ?',
                (id,)
            ).fetchone()[0]
            
            if req_count > 0:
                return jsonify({
                    "error": f"Cannot delete analysis with {req_count} related requirements. Delete requirements first."
                }), 400
            
            # Safe to delete
            conn.execute('DELETE FROM scenario_analyses WHERE id = ?', (id,))
            conn.commit()
            
            return jsonify({"status": "success"})
    except Exception as e:
        logger.exception(f"Error deleting analysis {id}")
        return jsonify({"error": "Failed to delete analysis"}), 500


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

if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", "8080"))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() in ("1", "true", "yes")
    app.run(host=host, port=port, debug=debug)
