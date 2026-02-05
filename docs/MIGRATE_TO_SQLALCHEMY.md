Migration plan: move from raw sqlite3 schema to SQLAlchemy ORM

Goal
- Migrate `database.py` table definitions to SQLAlchemy models and use SQLAlchemy Core/ORM for DB access.
- Replace raw SQL usage in `app.py` with parameterized queries via SQLAlchemy session.
- Maintain existing data and add migration steps.

High-level steps
1. Add SQLAlchemy dependency to `requirements.txt` (e.g., SQLAlchemy>=1.4, alembic for migrations).
2. Create `models.py` and define ORM models for each table (columns below).
3. Create a new `db.py` that sets up `engine`, `SessionLocal`, and `Base`.
4. Gradually replace `get_db_connection()` and `db_conn()` usages in `app.py` with SQLAlchemy session dependency.
5. Write Alembic migration scripts to create tables (or export current schema and data to a migration).
6. Run tests and update code where raw SQL relied on SQLite-specific functions.
7. Remove old `database.py` once migration validated and data imported.

Recommended timeline
- Phase 1 (1-2 days): Add dependencies, create `models.py` and `db.py`, scaffold Alembic.
- Phase 2 (2-3 days): Migrate simple read endpoints to use ORM and validate responses.
- Phase 3 (2-3 days): Migrate write endpoints and integrate transactions.
- Phase 4 (1-2 days): Run full integration tests and finalize migration.

Key considerations
- SQLite->Postgres differences: datatypes, concurrency, JSON handling.
- Preserve existing `project_copilot.db` by creating a dump and importing via migration scripts.
- Add tests to ensure API parity.

Tables and columns (to implement as SQLAlchemy models)
- requirements: id, project_id, code, title, module, complexity, status, ai_status, effort_days, summary
- projects: id, project_code, project_name, customer_name, start_date, end_date, status, modules, environment, description, customer_industry, customer_country, customer_contact, customer_email, deployment_type, implementation_approach, sap_modules, golive_planned, golive_actual, project_manager, solution_architect, functional_lead, technical_lead, total_budget, current_phase, completion_percent, created_at
- analysis_sessions: id, project_id, scenario_id, session_name, session_code, module, process_name, session_date, facilitator, status, notes, created_at
- questions: id, session_id, question_id, question_text, category, question_order, is_mandatory, answer_text, answered_by, status, created_at
- answers: id, question_id, answer_text, answered_by, answered_at, confidence_score
- fitgap: id, session_id, project_id, gap_id, process_name, gap_description, impact_area, solution_type, risk_level, effort_estimate, priority, status, notes, created_at
- fs_ts_documents: id, requirement_id, document_type, version, content, template_used, status, approved_by, approved_at, file_path, sharepoint_url, created_at, updated_at
- test_cases: id, fs_ts_id, test_case_id, test_scenario, test_type, preconditions, test_steps, expected_result, status, environment, executed_by, executed_at, alm_reference, created_at
- audit_log: id, table_name, record_id, action, old_values, new_values, changed_by, changed_at
- scenarios: id, project_id, scenario_id, name, module, description, status, level, parent_id, created_at
- session_attendees: id, session_id, name, role, department, email, status, created_at
- session_agenda: id, session_id, item_order, topic, description, duration_minutes, presenter, status, notes, created_at
- meeting_minutes: id, session_id, minute_order, topic, discussion, content, key_points, recorded_by, created_at
- action_items: id, session_id, project_id, action_id, title, description, assigned_to, due_date, priority, status, source, related_gap_id, created_at
- decisions: id, session_id, project_id, decision_id, topic, description, options_considered, decision_made, rationale, decision_maker, decision_date, impact_areas, status, related_gap_id, created_at
- risks_issues: id, session_id, project_id, item_id, title, description, item_type, type, probability, impact_level, risk_score, status, owner, mitigation, contingency, created_at
- analyses: id, session_id, analysis_type, title, content, status, created_at
- new_requirements: id, session_id, project_id, gap_id, title, description, module, fit_type, classification, priority, status, conversion_status, converted_item_type, converted_item_id, converted_at, converted_by, created_at
- wricef_items: id, project_id, requirement_id, code, title, description, wricef_type, module, complexity, effort_days, status, owner, fs_content, ts_content, unit_test_steps, created_at
- config_items: id, project_id, requirement_id, code, title, description, config_type, module, status, owner, config_details, unit_test_steps, created_at
- wricef: id, code, wricef_id, title, wricef_type, module, status
- test_management: id, project_id, code, test_type, title, description, status, owner, source_type, source_id, steps, created_at, updated_at

If you want, I can now:
- Replace any remaining direct `sqlite3` usage in `app.py` to use SQLAlchemy session (incrementally), or
- Generate `models.py` and `db.py` scaffolding and an initial Alembic config.

Which next step do you prefer?