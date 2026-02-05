from flask import Flask, render_template, jsonify, request
import sqlite3
import os

app = Flask(__name__)

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), 'project_copilot.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

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
        conn = get_db_connection()
        projects = conn.execute('SELECT * FROM projects ORDER BY created_at DESC').fetchall()
        conn.close()
        return jsonify([dict(row) for row in projects])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/projects", methods=["POST"])
def add_project():
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute("""INSERT INTO projects (
            project_code, project_name, description, status,
            customer_name, customer_industry, customer_country,
            customer_contact, customer_email, deployment_type,
            implementation_approach, sap_modules, start_date,
            golive_planned, golive_actual, project_manager,
            solution_architect, functional_lead, technical_lead,
            total_budget, current_phase, completion_percent
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (data.get("project_code"), data.get("project_name"), data.get("description"),
             data.get("status", "Planning"), data.get("customer_name"), data.get("customer_industry"),
             data.get("customer_country"), data.get("customer_contact"), data.get("customer_email"),
             data.get("deployment_type"), data.get("implementation_approach"), data.get("sap_modules"),
             data.get("start_date"), data.get("golive_planned"), data.get("golive_actual"),
             data.get("project_manager"), data.get("solution_architect"), data.get("functional_lead"),
             data.get("technical_lead"), data.get("total_budget"), data.get("current_phase"),
             data.get("completion_percent", 0)))
        conn.commit()
        new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()
        return jsonify({"status": "success", "id": new_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/projects/<int:project_id>', methods=['GET'])
def get_project_detail(project_id):
    """Tek bir projenin detayini getir"""
    try:
        conn = get_db_connection()
        project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
        conn.close()
        if project:
            return jsonify(dict(project))
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/projects/<int:id>", methods=["PUT"])
def update_project(id):
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute("""UPDATE projects SET 
            project_code = ?, project_name = ?, description = ?, status = ?,
            customer_name = ?, customer_industry = ?, customer_country = ?,
            customer_contact = ?, customer_email = ?, deployment_type = ?,
            implementation_approach = ?, sap_modules = ?, start_date = ?,
            golive_planned = ?, golive_actual = ?, project_manager = ?,
            solution_architect = ?, functional_lead = ?, technical_lead = ?,
            total_budget = ?, current_phase = ?, completion_percent = ?
            WHERE id = ?""",
            (data.get("project_code"), data.get("project_name"), data.get("description"),
             data.get("status"), data.get("customer_name"), data.get("customer_industry"),
             data.get("customer_country"), data.get("customer_contact"), data.get("customer_email"),
             data.get("deployment_type"), data.get("implementation_approach"), data.get("sap_modules"),
             data.get("start_date"), data.get("golive_planned"), data.get("golive_actual"),
             data.get("project_manager"), data.get("solution_architect"), data.get("functional_lead"),
             data.get("technical_lead"), data.get("total_budget"), data.get("current_phase"),
             data.get("completion_percent"), id))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/projects/<int:id>", methods=["DELETE"])
def delete_project(id):
    try:
        conn = get_db_connection()
        conn.execute("DELETE FROM projects WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
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

# ============== NEW REQUIREMENTS API ==============
@app.route('/api/new_requirements', methods=['GET'])
def get_new_requirements():
    project_id = request.args.get('project_id')
    session_id = request.args.get('session_id')
    try:
        conn = get_db_connection()
        if session_id:
            rows = conn.execute('SELECT * FROM new_requirements WHERE session_id = ? ORDER BY created_at DESC', (session_id,)).fetchall()
        elif project_id:
            rows = conn.execute('SELECT * FROM new_requirements WHERE project_id = ? ORDER BY created_at DESC', (project_id,)).fetchall()
        else:
            rows = conn.execute('SELECT * FROM new_requirements ORDER BY created_at DESC').fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/new_requirements', methods=['POST'])
def add_new_requirement():
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO new_requirements (session_id, project_id, gap_id, title, description, module, fit_type, classification, priority, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (data.get('session_id'), data.get('project_id'), data.get('gap_id'), data['title'], data.get('description'), data.get('module'), data.get('fit_type'), data.get('classification', 'Gap'), data.get('priority','Medium'), data.get('status','Draft')))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/new_requirements/<int:req_id>', methods=['GET'])
def get_new_requirement_detail(req_id):
    try:
        conn = get_db_connection()
        row = conn.execute('SELECT * FROM new_requirements WHERE id = ?', (req_id,)).fetchone()
        conn.close()
        if row:
            return jsonify(dict(row))
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/new_requirements/<int:req_id>', methods=['PUT'])
def update_new_requirement(req_id):
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute('''
            UPDATE new_requirements SET title = ?, description = ?, classification = ?, priority = ?, status = ?
            WHERE id = ?
        ''', (data.get('title'), data.get('description'), data.get('classification'), data.get('priority'), data.get('status'), req_id))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
        conn.execute('''
            UPDATE wricef_items SET title = ?, description = ?, wricef_type = ?, module = ?, complexity = ?, effort_days = ?, status = ?, owner = ?
            WHERE id = ?
        ''', (data.get('title'), data.get('description'), data.get('wricef_type'), data.get('module'), data.get('complexity'), data.get('effort_days'), data.get('status'), data.get('owner'), item_id))
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
        conn.execute('''
            UPDATE config_items SET title = ?, description = ?, config_type = ?, module = ?, status = ?, owner = ?, config_details = ?
            WHERE id = ?
        ''', (data.get('title'), data.get('description'), data.get('config_type'), data.get('module'), data.get('status'), data.get('owner'), data.get('config_details'), item_id))
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

# ============== TEST MANAGEMENT API ==============
@app.route('/api/test_management', methods=['GET'])
def get_test_management():
    project_id = request.args.get('project_id')
    try:
        conn = get_db_connection()
        if project_id:
            rows = conn.execute('SELECT * FROM test_management WHERE project_id = ? ORDER BY created_at DESC', (project_id,)).fetchall()
        else:
            rows = conn.execute('SELECT * FROM test_management ORDER BY created_at DESC').fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
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
    project_id = request.args.get('project_id')
    try:
        conn = get_db_connection()
        if project_id:
            scenarios = conn.execute('SELECT * FROM scenarios WHERE project_id = ? ORDER BY created_at DESC', (project_id,)).fetchall()
        else:
            scenarios = conn.execute('SELECT * FROM scenarios ORDER BY created_at DESC').fetchall()
        conn.close()
        return jsonify([dict(s) for s in scenarios])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/scenarios', methods=['POST'])
def add_scenario():
    try:
        data = request.json
        project_id = data.get('project_id')
        conn = get_db_connection()
        
        # Otomatik ID üret
        auto_id = generate_auto_id(project_id, "S") if project_id else None
        
        conn.execute('''
            INSERT INTO scenarios (scenario_id, project_id, name, description, process_area, priority, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (auto_id, project_id, data.get('name'), data.get('description'),
              data.get('process_area'), data.get('priority', 'Medium'), data.get('status', 'Draft')))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "scenario_id": auto_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/scenarios/<int:id>', methods=['GET'])
def get_scenario_by_id(id):
    try:
        conn = get_db_connection()
        scenario = conn.execute('SELECT * FROM scenarios WHERE id = ?', (id,)).fetchone()
        conn.close()
        if scenario:
            return jsonify(dict(scenario))
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/scenarios/<int:id>', methods=['PUT'])
def update_scenario(id):
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute('''
            UPDATE scenarios SET name = ?, description = ?, process_area = ?, priority = ?, status = ?
            WHERE id = ?
        ''', (data.get('name'), data.get('description'), data.get('process_area'),
              data.get('priority'), data.get('status'), id))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/scenarios/<int:id>', methods=['DELETE'])
def delete_scenario(id):
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM scenarios WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
