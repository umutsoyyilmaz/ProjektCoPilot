from flask import Flask, render_template, jsonify, request
import sqlite3
import os

app = Flask(__name__)


def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), "project_copilot.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def index():
    try:
        conn = get_db_connection()

        # Tüm requirements (Requirements sayfası için)
        requirements = conn.execute("SELECT * FROM requirements").fetchall()

        # Recent Activities (Son 5 değişiklik)
        recent_activities = conn.execute("""
            SELECT * FROM requirements 
            ORDER BY id DESC 
            LIMIT 5
        """).fetchall()

        conn.close()
        return render_template(
            "index.html", requirements=requirements, recent_activities=recent_activities
        )
    except Exception as e:
        return f"Veritabanı hatası: {e}"


@app.route("/api/requirements", methods=["GET"])
def get_requirements():
    """Tum requirementlari listele"""
    project_id = request.args.get("project_id")
    try:
        conn = get_db_connection()
        if project_id:
            requirements = conn.execute(
                "SELECT * FROM requirements WHERE project_id = ? ORDER BY id DESC",
                (project_id,),
            ).fetchall()
        else:
            requirements = conn.execute(
                "SELECT * FROM requirements ORDER BY id DESC"
            ).fetchall()
        conn.close()
        return jsonify([dict(row) for row in requirements])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/requirements", methods=["POST"])
def add_requirement():
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO requirements (project_id, code, title, module, complexity, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                data.get("project_id"),
                data["code"],
                data["title"],
                data["module"],
                data["complexity"],
                "Draft",
            ),
        )
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# EKSİK OLAN VE SORUNA YOL AÇAN KISIM BURASIYDI:
@app.route("/api/requirements/<int:req_id>")
def get_requirement_detail(req_id):
    try:
        conn = get_db_connection()
        requirement = conn.execute(
            "SELECT * FROM requirements WHERE id = ?", (req_id,)
        ).fetchone()
        conn.close()
        if requirement:
            return jsonify(dict(requirement))
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    return jsonify({"reply": f"Mesajınızı aldım: '{data.get('message')}'"})


# ============== PROJECTS API ==============


@app.route("/api/projects", methods=["GET"])
def get_projects():
    """Tum projeleri listele"""
    try:
        conn = get_db_connection()
        projects = conn.execute(
            "SELECT * FROM projects ORDER BY created_at DESC"
        ).fetchall()
        conn.close()
        return jsonify([dict(row) for row in projects])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/projects", methods=["POST"])
def add_project():
    """Yeni proje ekle"""
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO projects (project_code, project_name, customer_name, status, modules, environment, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                data["project_code"],
                data["project_name"],
                data.get("customer_name"),
                data.get("status", "Planning"),
                data.get("modules"),
                data.get("environment"),
                data.get("description"),
            ),
        )
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/projects/<int:project_id>", methods=["GET"])
def get_project_detail(project_id):
    """Tek bir projenin detayini getir"""
    try:
        conn = get_db_connection()
        project = conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        conn.close()
        if project:
            return jsonify(dict(project))
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============== ANALYSIS SESSIONS API ==============


@app.route("/api/sessions", methods=["GET"])
@app.route("/api/sessions", methods=["GET"])
def get_sessions():
    """Tum analiz oturumlarini listele"""
    project_id = request.args.get("project_id")
    try:
        conn = get_db_connection()
        if project_id:
            sessions = conn.execute(
                """
                SELECT s.*, p.project_name
                FROM analysis_sessions s
                LEFT JOIN projects p ON s.project_id = p.id
                WHERE s.project_id = ?
                ORDER BY s.created_at DESC
            """,
                (project_id,),
            ).fetchall()
        else:
            sessions = conn.execute("""
                SELECT s.*, p.project_name
                FROM analysis_sessions s
                LEFT JOIN projects p ON s.project_id = p.id
                ORDER BY s.created_at DESC
            """).fetchall()
        conn.close()
        return jsonify([dict(row) for row in sessions])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sessions/<int:session_id>", methods=["GET"])
def get_session_detail(session_id):
    """Tek bir session detayi"""
    try:
        conn = get_db_connection()
        session = conn.execute(
            """
            SELECT s.*, p.project_name
            FROM analysis_sessions s
            LEFT JOIN projects p ON s.project_id = p.id
            WHERE s.id = ?
        """,
            (session_id,),
        ).fetchone()
        conn.close()
        if session:
            return jsonify(dict(session))
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sessions", methods=["POST"])
def add_session():
    """Yeni analiz oturumu ekle"""
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO analysis_sessions (project_id, session_name, module, process_name, facilitator, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                data["project_id"],
                data["session_name"],
                data.get("module"),
                data.get("process_name"),
                data.get("facilitator"),
                data.get("status", "Planned"),
                data.get("notes"),
            ),
        )
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============== QUESTIONS API ==============


@app.route("/api/questions", methods=["GET"])
def get_questions():
    """Sorulari listele"""
    session_id = request.args.get("session_id")
    try:
        conn = get_db_connection()
        if session_id:
            questions = conn.execute(
                """
                SELECT q.*, a.answer_text
                FROM questions q
                LEFT JOIN answers a ON q.id = a.question_id
                WHERE q.session_id = ?
                ORDER BY q.created_at ASC
            """,
                (session_id,),
            ).fetchall()
        else:
            questions = conn.execute("""
                SELECT q.*, a.answer_text
                FROM questions q
                LEFT JOIN answers a ON q.id = a.question_id
                ORDER BY q.created_at DESC
            """).fetchall()
        conn.close()
        return jsonify([dict(row) for row in questions])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/questions", methods=["POST"])
def add_question():
    """Yeni soru ekle"""
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.execute(
            """
            INSERT INTO questions (session_id, question_text, created_at)
            VALUES (?, ?, datetime('now'))
        """,
            (data.get("session_id"), data.get("question_text")),
        )
        question_id = cursor.lastrowid

        # Eger cevap da varsa ekle
        if data.get("answer_text"):
            conn.execute(
                """
                INSERT INTO answers (question_id, answer_text, answered_at)
                VALUES (?, ?, datetime('now'))
            """,
                (question_id, data.get("answer_text")),
            )

        conn.commit()
        conn.close()
        return jsonify({"success": True, "id": question_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============== FITGAP API ==============


@app.route("/api/fitgap", methods=["GET"])
def get_fitgap():
    """Tum FitGap kayitlarini listele"""
    session_id = request.args.get("session_id")
    try:
        conn = get_db_connection()
        if session_id:
            gaps = conn.execute(
                "SELECT * FROM fitgap WHERE session_id = ? ORDER BY created_at DESC",
                (session_id,),
            ).fetchall()
        else:
            gaps = conn.execute(
                "SELECT * FROM fitgap ORDER BY created_at DESC"
            ).fetchall()
        conn.close()
        return jsonify([dict(row) for row in gaps])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/fitgap", methods=["POST"])
def add_fitgap():
    """Yeni FitGap kaydi ekle"""
    try:
        data = request.json
        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO fitgap (session_id, gap_id, process_name, gap_description, impact_area, solution_type, risk_level, effort_estimate, priority, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                data["session_id"],
                data["gap_id"],
                data.get("process_name"),
                data.get("description"),
                data.get("impact_area"),
                data.get("resolution_type"),
                data.get("risk_level"),
                data.get("effort_estimate"),
                data.get("priority", "Medium"),
                data.get("status", "Identified"),
                data.get("notes"),
            ),
        )
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============== DASHBOARD STATS API ==============


@app.route("/api/dashboard/stats", methods=["GET"])
def get_dashboard_stats():
    """Dashboard icin istatistikler - proje bazli filtreleme destekli"""
    project_id = request.args.get("project_id")
    try:
        conn = get_db_connection()

        if project_id:
            # Proje seçiliyse sadece o projenin verileri
            total_sessions = conn.execute(
                "SELECT COUNT(*) FROM analysis_sessions WHERE project_id = ?",
                (project_id,),
            ).fetchone()[0]
            total_gaps = conn.execute(
                """
                SELECT COUNT(*) FROM fitgap f
                JOIN analysis_sessions s ON f.session_id = s.id
                WHERE s.project_id = ?
            """,
                (project_id,),
            ).fetchone()[0]
            total_questions = conn.execute(
                """
                SELECT COUNT(*) FROM questions q
                JOIN analysis_sessions s ON q.session_id = s.id
                WHERE s.project_id = ?
            """,
                (project_id,),
            ).fetchone()[0]

            # Recent activities for this project
            recent_activities = conn.execute(
                """
                SELECT * FROM analysis_sessions 
                WHERE project_id = ? 
                ORDER BY created_at DESC LIMIT 5
            """,
                (project_id,),
            ).fetchall()

            # Project info
            project = conn.execute(
                "SELECT * FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
            project_name = project["project_name"] if project else "Unknown"
            project_status = project["status"] if project else "Unknown"
        else:
            # Proje seçili değilse genel istatistikler
            total_sessions = conn.execute(
                "SELECT COUNT(*) FROM analysis_sessions"
            ).fetchone()[0]
            total_gaps = conn.execute("SELECT COUNT(*) FROM fitgap").fetchone()[0]
            total_questions = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[
                0
            ]
            recent_activities = []
            project_name = "All Projects"
            project_status = "-"

        # Genel sayılar (her zaman)
        total_projects = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        total_requirements = conn.execute(
            "SELECT COUNT(*) FROM requirements"
        ).fetchone()[0]

        conn.close()

        return jsonify(
            {
                "total_projects": total_projects,
                "total_requirements": total_requirements,
                "total_sessions": total_sessions,
                "total_gaps": total_gaps,
                "total_questions": total_questions,
                "project_name": project_name,
                "project_status": project_status,
                "recent_activities": [dict(row) for row in recent_activities],
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
