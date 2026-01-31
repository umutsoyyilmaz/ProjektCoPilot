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

@app.route('/api/requirements', methods=['POST'])
def add_requirement():
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO requirements (code, title, module, complexity, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (data['code'], data['title'], data['module'], data['complexity'], 'Draft'))
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
def get_sessions():
    """Tum analiz oturumlarini listele"""
    try:
        conn = get_db_connection()
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

# ============== FITGAP API ==============

@app.route('/api/fitgap', methods=['GET'])
def get_fitgap():
    """Tum FitGap kayitlarini listele"""
    try:
        conn = get_db_connection()
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
        ''', (data['session_id'], data['gap_id'], data.get('process_name'), data.get('gap_description'),
              data.get('impact_area'), data.get('solution_type'), data.get('risk_level'),
              data.get('effort_estimate'), data.get('priority', 'Medium'), data.get('status', 'Identified'), data.get('notes')))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============== DASHBOARD STATS API ==============

@app.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    """Dashboard icin istatistikler"""
    try:
        conn = get_db_connection()
        
        # Toplam sayilar
        total_projects = conn.execute('SELECT COUNT(*) FROM projects').fetchone()[0]
        total_requirements = conn.execute('SELECT COUNT(*) FROM requirements').fetchone()[0]
        total_sessions = conn.execute('SELECT COUNT(*) FROM analysis_sessions').fetchone()[0]
        total_gaps = conn.execute('SELECT COUNT(*) FROM fitgap').fetchone()[0]
        
        # Status dagilimi
        req_by_status = conn.execute('''
            SELECT status, COUNT(*) as count FROM requirements GROUP BY status
        ''').fetchall()
        
        # Module dagilimi
        req_by_module = conn.execute('''
            SELECT module, COUNT(*) as count FROM requirements GROUP BY module
        ''').fetchall()
        
        conn.close()
        
        return jsonify({
            "total_projects": total_projects,
            "total_requirements": total_requirements,
            "total_sessions": total_sessions,
            "total_gaps": total_gaps,
            "requirements_by_status": [dict(row) for row in req_by_status],
            "requirements_by_module": [dict(row) for row in req_by_module]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
