from flask import Flask, render_template, jsonify, request
import sqlite3
import os

app = Flask(__name__)

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), 'project_copilot.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

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

@app.route('/api/projects', methods=['POST'])
def add_project():
    """Yeni proje ekle"""
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO projects (project_code, project_name, customer_name, status, modules, environment, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (data['project_code'], data['project_name'], data.get('customer_name'), 
              data.get('status', 'Planning'), data.get('modules'), data.get('environment'), data.get('description')))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 200
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

# ============== ANALYSIS SESSIONS API ==============

@app.route('/api/sessions', methods=['GET'])
@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    """Tum analiz oturumlarini listele"""
    project_id = request.args.get('project_id')
    try:
        conn = get_db_connection()
        if project_id:
            sessions = conn.execute('''
                SELECT s.*, p.project_name
                FROM analysis_sessions s
                LEFT JOIN projects p ON s.project_id = p.id
                WHERE s.project_id = ?
                ORDER BY s.created_at DESC
            ''', (project_id,)).fetchall()
        else:
            sessions = conn.execute('''
                SELECT s.*, p.project_name
                FROM analysis_sessions s
                LEFT JOIN projects p ON s.project_id = p.id
                ORDER BY s.created_at DESC
            ''').fetchall()
        conn.close()
        return jsonify([dict(row) for row in sessions])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/sessions/<int:session_id>', methods=['GET'])
def get_session_detail(session_id):
    """Tek bir session detayi"""
    try:
        conn = get_db_connection()
        session = conn.execute('''
            SELECT s.*, p.project_name
            FROM analysis_sessions s
            LEFT JOIN projects p ON s.project_id = p.id
            WHERE s.id = ?
        ''', (session_id,)).fetchone()
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
            INSERT INTO analysis_sessions (project_id, session_name, module, process_name, facilitator, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (data['project_id'], data['session_name'], data.get('module'), 
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

@app.route('/api/questions', methods=['POST'])
def add_question():
    """Yeni soru ekle"""
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.execute('''
            INSERT INTO questions (session_id, question_text, created_at)
            VALUES (?, ?, datetime('now'))
        ''', (data.get('session_id'), data.get('question_text')))
        question_id = cursor.lastrowid
        
        # Eger cevap da varsa ekle
        if data.get('answer_text'):
            conn.execute('''
                INSERT INTO answers (question_id, answer_text, answered_at)
                VALUES (?, ?, datetime('now'))
            ''', (question_id, data.get('answer_text')))
        
        conn.commit()
        conn.close()
        return jsonify({"success": True, "id": question_id}), 201
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

@app.route('/api/fitgap', methods=['POST'])
def add_fitgap():
    """Yeni FitGap kaydi ekle"""
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO fitgap (session_id, gap_id, process_name, gap_description, impact_area, solution_type, risk_level, effort_estimate, priority, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (data['session_id'], data['gap_id'], data.get('process_name'), data.get('description'), 
              data.get('impact_area'), data.get('resolution_type'), data.get('risk_level'),
              data.get('effort_estimate'), data.get('priority', 'Medium'), data.get('status', 'Identified'), data.get('notes')))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 200
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
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
