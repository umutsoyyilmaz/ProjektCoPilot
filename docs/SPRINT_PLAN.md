# 🚀 ProjektCoPilot - Sprint Execution Plan

**Oluşturma Tarihi:** 2026-02-05  
**Hedef:** models.py tabanlı tam PRD uyumlu sistem  
**Süre:** 6 Sprint (12 hafta)

---

## 📊 Mevcut Durum Özeti

| Katman | Tamamlanma | Kritik Eksikler |
|--------|-----------|-----------------|
| **CORE** | 60% | Analysis entity, Scenario composite, Detail UI'lar |
| **TEST** | 35% | TestCycle, TestExecution, Defect (tüm katman) |
| **AI** | 0% | Tüm AI layer |
| **Infrastructure** | 40% | models.py entegrasyonu, SQLAlchemy migration |

---

## 🎯 SPRINT 0: Foundation Upgrade (2 hafta)
**Amaç:** Raw SQL'den SQLAlchemy'ye geçiş, models.py entegrasyonu

### Sprint Hedefleri
- [ ] Flask-SQLAlchemy setup
- [ ] models.py → app.py entegrasyonu
- [ ] Mevcut tablolar için SQLAlchemy model migration
- [ ] Test suite update (raw SQL → ORM)

### Detaylı İşler

#### Backend (Efor: L)
1. **SQLAlchemy Setup**
   ```python
   # app.py
   from models import db, Project, Scenario, Requirement, WricefItem, ConfigItem
   
   app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project_copilot.db'
   app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
   db.init_app(app)
   ```

2. **Mevcut API'leri ORM'e migrate et** (öncelik sırasıyla):
   - [ ] Projects endpoints (5 endpoint)
   - [ ] Scenarios endpoints (5 endpoint)
   - [ ] Requirements endpoints (6 endpoint)
   - [ ] WRICEF endpoints (6 endpoint)
   - [ ] Config endpoints (6 endpoint)
   - [ ] Test Management (4 endpoint)

3. **generate_code helper'ı models.py'dan kullan**
   ```python
   from models import generate_code
   new_code = generate_code(Requirement, project_id, 'REQ')
   ```

#### Testing (Efor: M)
- [ ] test_app.py'yi ORM'e göre güncelle
- [ ] Tüm testlerin pass olduğunu doğrula (17 test)
- [ ] Yeni testler: ORM relationship'ler için

#### Çıktı
- ✅ Tüm mevcut API'ler SQLAlchemy ile çalışır
- ✅ database.py deprecated olur, sadece migration için kalır
- ✅ Test coverage: %90+

**Bağımlılık:** YOK  
**Risk:** Legacy kod kırılma riski → İyi test coverage gerekli

---

## 🎯 SPRINT 1: Core Layer Completion (2 hafta)
**Amaç:** Analysis entity + Scenario composite + UI detail modals

### Sprint Hedefleri
- [ ] Analysis entity (CRUD + API)
- [ ] Scenario composite support
- [ ] Requirement → WRICEF/Config convert UI
- [ ] Detail modals: WRICEF, Config, Requirement

### Detaylı İşler

#### Backend - Analysis Entity (Efor: M)
1. **DB Schema** (models.py'de zaten var)
   ```python
   class Analysis(db.Model):
       id, scenario_id, code, name, description, analysis_type, 
       conducted_date, participants, findings, status, created_at, updated_at
   ```

2. **API Endpoints**
   ```python
   GET/POST   /api/scenarios/<sid>/analyses
   GET/PUT/DEL /api/analyses/<id>
   ```

3. **Migration**: analysis_sessions → Analysis relation
   - `new_requirements.session_id` → `analysis_id`
   - Workshop data kalsın, ama Analysis ile ilişkilendirilsin

#### Backend - Scenario Composite (Efor: S)
1. **DB Update**
   ```python
   class Scenario(db.Model):
       is_composite = db.Column(db.Boolean, default=False)
       included_scenario_ids = db.Column(db.JSON)  # [1,2,3]
   ```

2. **API Enhancement**
   ```python
   PUT /api/scenarios/<id>  # is_composite + included_scenario_ids
   ```

#### Frontend - Detail Modals (Efor: L)
1. **Requirement Detail Modal**
   - Classification badge (Fit/PartialFit/Gap)
   - "Convert to WRICEF" / "Convert to Config" butonları
   - Converted item linki (eğer dönüştürülmüşse)

2. **WRICEF Detail Modal** (4 tab)
   - **Tab 1:** Basic Info (title, type, module, complexity, owner)
   - **Tab 2:** FS Content (WYSIWYG editor)
   - **Tab 3:** TS Content (WYSIWYG editor)
   - **Tab 4:** Unit Test Steps (JSON array editor)
   - **Action:** "Convert to Unit Test" butonu

3. **Config Detail Modal** (3 tab)
   - **Tab 1:** Basic Info
   - **Tab 2:** Config Details (JSON editor: SSCUI, IMG path, parameters)
   - **Tab 3:** Unit Test Steps
   - **Action:** "Convert to Unit Test" butonu

4. **Scenario Composite UI**
   - Multi-select dropdown (other scenarios)
   - "Create Composite Scenario" butonu

#### Testing (Efor: M)
- [ ] Analysis CRUD tests
- [ ] Scenario composite creation test
- [ ] Convert flow UI test (manual QA)

#### Çıktı
- ✅ Scenario → Analysis → Requirement zinciri tam
- ✅ Composite scenario oluşturulabilir
- ✅ Requirement convert UI tam fonksiyonel
- ✅ WRICEF/Config detail ekranları FS/TS editor ile

**Bağımlılık:** Sprint 0 (ORM migration)  
**Risk:** Frontend modal complexity → İnkremental geliştir

---

## 🎯 SPRINT 2: Test Cycle & Execution (2 hafta)
**Amaç:** Test yönetimini cycle-execution seviyesine taşı

### Sprint Hedefleri
- [ ] TestCycle entity (CRUD + API)
- [ ] TestExecution entity (CRUD + API)
- [ ] Test Case → Execution bağlantısı
- [ ] Entry/Exit criteria check

### Detaylı İşler

#### Backend - TestCycle (Efor: M)
1. **DB Schema** (models.py'de var)
   ```python
   class TestCycle(db.Model):
       id, project_id, code, name, test_type, start_date, end_date,
       status, entry_criteria (JSON), exit_criteria (JSON),
       target_pass_rate, notes
   ```

2. **API Endpoints**
   ```python
   GET/POST   /api/projects/<pid>/test-cycles
   GET/PUT/DEL /api/test-cycles/<id>
   POST       /api/test-cycles/<id>/check-entry-criteria
   POST       /api/test-cycles/<id>/check-exit-criteria
   ```

3. **Business Logic**
   ```python
   # Entry/Exit criteria validation
   criteria = [
       {"criterion": "Tüm unit testler pass", "met": True},
       {"criterion": "Test ortamı hazır", "met": False}
   ]
   all_met = all(c['met'] for c in criteria)
   ```

#### Backend - TestExecution (Efor: M)
1. **DB Schema** (models.py'de var)
   ```python
   class TestExecution(db.Model):
       id, test_case_id, test_cycle_id, executed_by, executed_at,
       status, duration_minutes, step_results (JSON), evidence (JSON),
       notes
   ```

2. **API Endpoints**
   ```python
   GET/POST   /api/test-cycles/<cid>/executions
   GET/PUT    /api/test-executions/<id>
   POST       /api/test-executions/<id>/run      # Start execution
   POST       /api/test-executions/<id>/complete # Mark complete
   ```

3. **Step Results Format**
   ```json
   [
     {"step_no": 1, "status": "Passed", "actual": "Başarılı", "screenshot_url": null},
     {"step_no": 2, "status": "Failed", "actual": "Hata oluştu", "screenshot_url": "/uploads/..."}
   ]
   ```

#### Frontend - Test Cycle UI (Efor: L)
1. **Test Cycle List Page** (view-test-cycles)
   - Grid: Code, Name, Type, Dates, Status, Pass Rate
   - Create button

2. **Test Cycle Detail Modal** (5 tabs)
   - **Tab 1:** Basic Info
   - **Tab 2:** Entry Criteria (checklist + met status)
   - **Tab 3:** Assigned Test Cases (multi-select)
   - **Tab 4:** Executions List (nested table)
   - **Tab 5:** Exit Criteria + Summary

3. **Test Execution Modal**
   - Test case info (read-only)
   - Step-by-step execution form
   - Status dropdown for each step
   - "Upload Screenshot" for evidence
   - "Report Defect" button (Sprint 3'te aktifleşecek)

#### Testing (Efor: M)
- [ ] TestCycle CRUD tests
- [ ] TestExecution create/update tests
- [ ] Entry/exit criteria logic test

#### Çıktı
- ✅ Test cycle planlanabilir
- ✅ Test case'ler cycle'a atanır
- ✅ Execution adım adım kaydedilir
- ✅ Entry/exit criteria check çalışır

**Bağımlılık:** Sprint 1 (TestCase var)  
**Risk:** Step-by-step UI complexity → Başlangıçta basit tutalım

---

## 🎯 SPRINT 3: Defect Management (2 hafta)
**Amaç:** Defect lifecycle + SLA tracking + WRICEF linkage

### Sprint Hedefleri
- [ ] Defect entity (CRUD + API)
- [ ] TestExecution → Defect reporting
- [ ] Defect lifecycle state machine
- [ ] SLA calculation & breach tracking
- [ ] Defect → WRICEF optional linking

### Detaylı İşler

#### Backend - Defect Entity (Efor: L)
1. **DB Schema** (models.py'de var)
   ```python
   class Defect(db.Model):
       id, project_id, test_execution_id, wricef_id (optional),
       code, title, description, severity, priority, status,
       root_cause, reported_by, assigned_to, reported_at,
       resolved_at, sla_due_date, sla_breached, resolution_notes
   ```

2. **API Endpoints**
   ```python
   GET/POST   /api/projects/<pid>/defects
   GET/PUT/DEL /api/defects/<id>
   POST       /api/test-executions/<id>/report-defect
   POST       /api/defects/<id>/transition  # State machine
   GET        /api/defects/<id>/sla-status
   ```

3. **SLA Calculation** (.github/copilot-instructions.md Rule 3.4)
   ```python
   SLA_MATRIX = {
       ('Critical', 'Urgent'): 4,   # hours
       ('Major', 'High'): 8,
       ('Minor', 'Medium'): 24,
       ('Trivial', 'Low'): 48
   }
   
   def calculate_sla(defect):
       sla_hours = SLA_MATRIX.get((defect.severity, defect.priority))
       due_date = defect.reported_at + timedelta(hours=sla_hours)
       breached = datetime.now() > due_date and defect.status not in ['Closed', 'Verified']
       return due_date, breached
   ```

4. **Lifecycle State Machine** (.github/copilot-instructions.md Rule 3.5)
   ```python
   TRANSITIONS = {
       'New': ['Open'],
       'Open': ['Assigned'],
       'Assigned': ['InProgress'],
       'InProgress': ['Fixed', 'Rejected'],
       'Fixed': ['Retest'],
       'Retest': ['Verified', 'InProgress'],
       'Verified': ['Closed'],
       'Rejected': ['Closed']
   }
   
   def transition_defect(defect, new_status):
       if new_status not in TRANSITIONS.get(defect.status, []):
           raise ValueError(f"Invalid transition: {defect.status} → {new_status}")
       defect.status = new_status
   ```

#### Frontend - Defect Management UI (Efor: L)
1. **Defect List Page** (view-defects)
   - Grid: Code, Title, Severity, Priority, Status, SLA (red if breached), Assigned To
   - Filters: Severity, Priority, Status, SLA Breached
   - Create Defect button

2. **Defect Detail Modal** (4 tabs)
   - **Tab 1:** Basic Info (title, severity, priority, root cause)
   - **Tab 2:** Linked Items (test execution, WRICEF if linked)
   - **Tab 3:** Lifecycle (status transitions with timestamps)
   - **Tab 4:** Resolution (notes, attachments)
   - **Actions:** "Assign", "Start Work", "Mark Fixed", "Retest", "Close"

3. **Test Execution → Report Defect Flow**
   - "Report Defect" button in execution modal
   - Pre-fill: test_execution_id, test case info, failed step
   - Auto-calculate SLA due date
   - Auto-link to WRICEF if test case has source_type='WRICEF'

#### Testing (Efor: M)
- [ ] Defect CRUD tests
- [ ] SLA calculation tests
- [ ] State machine transition tests (valid/invalid)
- [ ] Defect reporting from execution test

#### Çıktı
- ✅ Defect oluşturulabilir (manual veya execution'dan)
- ✅ SLA otomatik hesaplanır ve breach track edilir
- ✅ Lifecycle state machine enforce edilir
- ✅ Defect → WRICEF bağlantısı kurulabilir

**Bağımlılık:** Sprint 2 (TestExecution)  
**Risk:** State machine complexity → Başlangıçta manual transition, sonra otomatik

---

## 🎯 SPRINT 4: UI Polish & Traceability (2 hafta)
**Amaç:** End-to-end traceability görselleştirme + UI iyileştirmeleri

### Sprint Hedefleri
- [ ] Traceability visualization
- [ ] Dashboard KPI widgets
- [ ] Batch operations (bulk assign, bulk update)
- [ ] Excel/PDF export

### Detaylı İşler

#### Frontend - Traceability View (Efor: M)
1. **Requirement Traceability Screen**
   - Tree view: Requirement → WRICEF/Config → Unit Tests → Defects
   - Click to navigate

2. **Test Coverage Report**
   - Scenario → Test Cases mapping
   - Coverage percentage
   - Untested scenarios highlight

3. **Defect Traceability**
   - Test Execution → Defect → WRICEF → Fix status
   - Timeline visualization

#### Frontend - Dashboard KPI Widgets (Efor: M)
1. **Test Progress Widget** (.github/copilot-instructions.md Section 8)
   ```sql
   SELECT tc.name, COUNT(te.id) AS total,
     SUM(CASE WHEN te.status='Passed' THEN 1 ELSE 0 END) AS passed,
     ROUND(100.0 * SUM(...) / NULLIF(COUNT(te.id),0), 1) AS pass_rate
   FROM test_cycle tc
   LEFT JOIN test_execution te ON te.test_cycle_id = tc.id
   WHERE tc.project_id = :pid
   GROUP BY tc.id
   ```

2. **Defect Summary Widget**
   ```sql
   SELECT severity, COUNT(*) AS count,
     SUM(CASE WHEN sla_breached=1 THEN 1 ELSE 0 END) AS breached
   FROM defect
   WHERE project_id = :pid AND status NOT IN ('Closed','Verified')
   GROUP BY severity
   ```

3. **Requirement Conversion Status**
   - Pie chart: Converted / Not Converted
   - Breakdown: CONFIG vs WRICEF

#### Backend - Batch Operations (Efor: S)
```python
POST /api/defects/bulk-assign
POST /api/test-cases/bulk-update-status
POST /api/requirements/bulk-convert
```

#### Backend - Export (Efor: M)
```python
GET /api/projects/<pid>/export/requirements.xlsx
GET /api/test-cycles/<id>/export/execution-report.pdf
```

#### Testing (Efor: S)
- [ ] Traceability query tests
- [ ] Dashboard KPI accuracy tests
- [ ] Export file generation tests

#### Çıktı
- ✅ End-to-end traceability görselleştirildi
- ✅ Dashboard KPI'ları canlı data gösterir
- ✅ Bulk operasyonlar hızlı çalışır
- ✅ Excel/PDF export çalışır

**Bağımlılık:** Sprint 1-3 (tüm entity'ler)  
**Risk:** Performance → Önce basit query'ler, sonra optimize et

---

## 🎯 SPRINT 5: AI Layer Foundation (2 hafta)
**Amaç:** AI entegrasyon altyapısı + ilk AI features

### Sprint Hedefleri
- [ ] AIInteractionLog entity
- [ ] AIEmbedding entity (vector search için)
- [ ] AI-powered test case generation
- [ ] AI-powered defect analysis
- [ ] Similar defect detection

### Detaylı İşler

#### Backend - AI Entities (Efor: M)
1. **AIInteractionLog** (models.py'de var)
   ```python
   class AIInteractionLog(db.Model):
       id, entity_type, entity_id, interaction_type,
       prompt, response, model_used, tokens_used,
       response_time_ms, success, error_message, created_at
   ```

2. **AIEmbedding** (models.py'de var)
   ```python
   class AIEmbedding(db.Model):
       id, entity_type, entity_id, embedding_vector (JSON),
       model_used, created_at
   ```

3. **API Endpoints**
   ```python
   POST /api/ai/chat
   POST /api/ai/generate-test-cases        # WRICEF/Config → Test steps
   POST /api/ai/analyze-defect             # Defect → Root cause suggestion
   POST /api/ai/find-similar-defects       # Vector search
   GET  /api/ai/interaction-log/<entity_type>/<entity_id>
   ```

#### Backend - AI Features (Efor: L)
1. **Test Case Generation** (OpenAI integration)
   ```python
   @app.route('/api/wricef-items/<id>/ai-generate-test', methods=['POST'])
   def ai_generate_test(id):
       wricef = WricefItem.query.get_or_404(id)
       
       prompt = f"""
       Generate unit test steps for this SAP development:
       Title: {wricef.title}
       Type: {wricef.wricef_type}
       FS: {wricef.fs_content}
       TS: {wricef.ts_content}
       
       Return JSON: [{{"step_no": 1, "action": "...", "input": "...", "expected": "..."}}]
       """
       
       response = openai.ChatCompletion.create(
           model="gpt-4",
           messages=[{"role": "user", "content": prompt}]
       )
       
       steps = json.loads(response.choices[0].message.content)
       
       # Log interaction
       log = AIInteractionLog(
           entity_type='WRICEF',
           entity_id=wricef.id,
           interaction_type='Generation',
           prompt=prompt,
           response=response.choices[0].message.content,
           model_used='gpt-4',
           tokens_used=response.usage.total_tokens,
           success=True
       )
       db.session.add(log)
       
       return jsonify(steps=steps)
   ```

2. **Defect Analysis** (ai_* columns in Defect model)
   ```python
   @app.route('/api/defects/<id>/ai-analyze', methods=['POST'])
   def ai_analyze_defect(id):
       defect = Defect.query.get_or_404(id)
       
       prompt = f"""
       Analyze this SAP defect:
       Title: {defect.title}
       Description: {defect.description}
       Test Steps: {defect.test_execution.step_results}
       
       Suggest:
       1. Root cause
       2. Severity justification
       3. Similar past defects
       4. Recommended fix approach
       """
       
       response = openai.ChatCompletion.create(...)
       
       analysis = json.loads(response.choices[0].message.content)
       
       # Update defect with AI suggestions
       defect.ai_suggested_root_cause = analysis['root_cause']
       defect.ai_suggested_severity = analysis['severity']
       defect.ai_analysis_summary = analysis['summary']
       defect.ai_recommended_fix = analysis['fix_approach']
       db.session.commit()
       
       return jsonify(analysis)
   ```

3. **Similar Defect Detection** (vector embeddings)
   ```python
   @app.route('/api/defects/<id>/find-similar', methods=['GET'])
   def find_similar_defects(id):
       defect = Defect.query.get_or_404(id)
       
       # Generate embedding if not exists
       if not defect.embedding:
           text = f"{defect.title} {defect.description}"
           embedding = openai.Embedding.create(
               model="text-embedding-ada-002",
               input=text
           ).data[0].embedding
           
           emb = AIEmbedding(
               entity_type='DEFECT',
               entity_id=defect.id,
               embedding_vector=json.dumps(embedding),
               model_used='text-embedding-ada-002'
           )
           db.session.add(emb)
       
       # Vector similarity search (cosine similarity)
       similar = find_similar_vectors(embedding, entity_type='DEFECT', top_k=5)
       
       defect.ai_similar_defects = json.dumps([
           {"defect_id": d.id, "defect_code": d.code, 
            "similarity": d.similarity, "title": d.title}
           for d in similar
       ])
       db.session.commit()
       
       return jsonify(similar_defects=similar)
   ```

#### Frontend - AI Features UI (Efor: M)
1. **WRICEF/Config Detail Modal**
   - "AI Generate Test Steps" button
   - Shows generated steps in preview
   - "Apply" or "Regenerate" buttons

2. **Defect Detail Modal**
   - "AI Analyze" button
   - Shows AI suggestions in new tab
   - Similar defects list with similarity score

3. **AI Interaction Log Viewer**
   - Shows all AI calls for an entity
   - Token usage, response time
   - Prompt/response inspector

#### Testing (Efor: M)
- [ ] AI API integration tests (mock responses)
- [ ] Embedding generation tests
- [ ] Vector similarity accuracy tests
- [ ] Token usage tracking tests

#### Çıktı
- ✅ AI test case generation çalışır
- ✅ Defect AI analysis suggestions üretir
- ✅ Similar defect detection embedding-based
- ✅ Tüm AI interactions log'lanır

**Bağımlılık:** Sprint 3 (Defect), Sprint 1 (WRICEF/Config)  
**Risk:** OpenAI API cost → Rate limiting + caching ekle

---

## 🎯 SPRINT 6: Polish & Production Ready (2 hafta)
**Amaç:** Production hazırlık, performans, güvenlik

### Sprint Hedefleri
- [ ] PostgreSQL migration (SQLite → PostgreSQL)
- [ ] Authentication & Authorization
- [ ] Audit logging
- [ ] Performance optimization
- [ ] Error handling & monitoring
- [ ] User documentation

### Detaylı İşler

#### Infrastructure (Efor: L)
1. **PostgreSQL Setup**
   ```python
   # Production config
   app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
       'DATABASE_URL',
       'postgresql://user:pass@localhost/projektcopilot'
   )
   ```

2. **Alembic Migrations**
   ```bash
   alembic init alembic
   alembic revision --autogenerate -m "Initial schema"
   alembic upgrade head
   ```

3. **Environment-based Config**
   ```python
   class Config:
       SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
       SECRET_KEY = os.getenv('SECRET_KEY')
       OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
   
   class DevelopmentConfig(Config):
       DEBUG = True
       SQLALCHEMY_ECHO = True
   
   class ProductionConfig(Config):
       DEBUG = False
       SQLALCHEMY_POOL_SIZE = 20
   ```

#### Security (Efor: M)
1. **Authentication** (Flask-Login)
   ```python
   from flask_login import LoginManager, login_required
   
   @app.route('/api/projects/<id>', methods=['PUT'])
   @login_required
   def update_project(id):
       ...
   ```

2. **Authorization** (Role-based)
   ```python
   class User(db.Model):
       id, username, email, password_hash, role
       # role: 'Admin', 'ProjectManager', 'Developer', 'Tester'
   
   def require_role(role):
       def decorator(f):
           @wraps(f)
           def wrapped(*args, **kwargs):
               if current_user.role != role:
                   abort(403)
               return f(*args, **kwargs)
           return wrapped
       return decorator
   
   @app.route('/api/projects', methods=['POST'])
   @login_required
   @require_role('Admin')
   def create_project():
       ...
   ```

3. **Input Validation** (marshmallow schemas)
   ```python
   from marshmallow import Schema, fields, validate
   
   class DefectSchema(Schema):
       title = fields.Str(required=True, validate=validate.Length(min=5, max=200))
       severity = fields.Str(required=True, validate=validate.OneOf(['Critical','Major','Minor','Trivial']))
       priority = fields.Str(required=True, validate=validate.OneOf(['Urgent','High','Medium','Low']))
   
   @app.route('/api/defects', methods=['POST'])
   def create_defect():
       schema = DefectSchema()
       errors = schema.validate(request.json)
       if errors:
           return jsonify(errors=errors), 400
       ...
   ```

#### Performance (Efor: M)
1. **Query Optimization**
   ```python
   # Eager loading to avoid N+1
   defects = Defect.query.options(
       db.joinedload(Defect.test_execution).joinedload(TestExecution.test_case)
   ).filter_by(project_id=pid).all()
   
   # Indexing
   class Defect(db.Model):
       __table_args__ = (
           db.Index('ix_defect_severity_status', 'severity', 'status'),
           db.Index('ix_defect_sla_breached', 'sla_breached'),
       )
   ```

2. **Caching** (Flask-Caching)
   ```python
   from flask_caching import Cache
   cache = Cache(app, config={'CACHE_TYPE': 'redis'})
   
   @app.route('/api/dashboard/stats')
   @cache.cached(timeout=300, key_prefix='dashboard_stats')
   def dashboard_stats():
       ...
   ```

3. **Pagination**
   ```python
   @app.route('/api/defects')
   def get_defects():
       page = request.args.get('page', 1, type=int)
       per_page = request.args.get('per_page', 20, type=int)
       
       pagination = Defect.query.paginate(page=page, per_page=per_page)
       
       return jsonify(
           items=[d.to_dict() for d in pagination.items],
           total=pagination.total,
           pages=pagination.pages,
           current_page=page
       )
   ```

#### Monitoring (Efor: S)
1. **Logging** (Python logging + Sentry)
   ```python
   import logging
   import sentry_sdk
   
   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)
   
   sentry_sdk.init(dsn=os.getenv('SENTRY_DSN'))
   
   @app.errorhandler(Exception)
   def handle_error(error):
       logger.error(f"Error: {error}", exc_info=True)
       sentry_sdk.capture_exception(error)
       return jsonify(error=str(error)), 500
   ```

2. **Health Check**
   ```python
   @app.route('/health')
   def health():
       try:
           db.session.execute('SELECT 1')
           return jsonify(status='healthy', db='ok'), 200
       except Exception as e:
           return jsonify(status='unhealthy', db=str(e)), 503
   ```

#### Documentation (Efor: M)
1. **API Documentation** (OpenAPI/Swagger)
   ```python
   from flask_swagger_ui import get_swaggerui_blueprint
   
   SWAGGER_URL = '/api/docs'
   API_URL = '/static/swagger.json'
   
   swaggerui_blueprint = get_swaggerui_blueprint(SWAGGER_URL, API_URL)
   app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)
   ```

2. **User Guide** (docs/)
   - Getting Started
   - User Roles & Permissions
   - Workflow Guide (Requirement → WRICEF → Test → Defect)
   - AI Features Guide
   - Troubleshooting

#### Testing (Efor: L)
- [ ] Load testing (Apache Bench / Locust)
- [ ] Security testing (SQL injection, XSS)
- [ ] End-to-end tests (Cypress)
- [ ] Test coverage: 85%+

#### Çıktı
- ✅ PostgreSQL production DB
- ✅ Authentication & role-based authorization
- ✅ API documentation (Swagger)
- ✅ Monitoring & error tracking (Sentry)
- ✅ Performance optimized (caching, indexing, pagination)
- ✅ User documentation complete
- ✅ Production deployment ready

**Bağımlılık:** Sprint 0-5 (tüm feature'lar)  
**Risk:** Migration hatası → Önce staging'de test et

---

## 📈 Sprint Summary & Metrics

| Sprint | Efor | Kritik Deliverable | Bağımlılık |
|--------|------|-------------------|------------|
| **Sprint 0** | L | SQLAlchemy migration | - |
| **Sprint 1** | L | Analysis entity + Convert UI | Sprint 0 |
| **Sprint 2** | L | Test Cycle/Execution | Sprint 1 |
| **Sprint 3** | L | Defect Management | Sprint 2 |
| **Sprint 4** | M | UI Polish + Traceability | Sprint 1-3 |
| **Sprint 5** | L | AI Layer | Sprint 1,3 |
| **Sprint 6** | L | Production Ready | Sprint 0-5 |

**Toplam Süre:** 12 hafta  
**Toplam Efor:** 6L + 1M = ~480 saat  
**Tahmini Takım:** 2 Full-time Developer

---

## 🎯 Critical Path

```
Sprint 0 (ORM) → Sprint 1 (Core) → Sprint 2 (Test Exec) → Sprint 3 (Defect) → Sprint 6 (Prod)
                      ↓
                 Sprint 4 (UI Polish) → Sprint 5 (AI)
```

**Paralel Çalışma Fırsatları:**
- Sprint 4 (frontend) ve Sprint 5 (AI backend) paralel olabilir
- Sprint 3'ten sonra defect management production'a alınabilir (early release)

---

## 🚨 Risk Mitigation

| Risk | Olasılık | Etki | Mitigation |
|------|----------|------|------------|
| ORM migration breaking existing code | Orta | Yüksek | İyi test coverage + incremental migration |
| AI API cost overrun | Orta | Orta | Rate limiting + caching + free tier kullanımı |
| Frontend complexity | Yüksek | Orta | Incremental development + UI library kullanımı |
| PostgreSQL migration issues | Düşük | Yüksek | Staging environment + backup strategy |
| Performance degradation | Orta | Orta | Load testing + query optimization + indexing |

---

## 📚 Reference Documents

- [`.github/copilot-instructions.md`](../.github/copilot-instructions.md) - Architecture & business rules
- [`models.py`](../models.py) - Target data model (SQLAlchemy)
- [`docs/newreq.md`](newreq.md) - PRD specification
- [`docs/PROGRESS_REPORT.md`](PROGRESS_REPORT.md) - Current status
- [`tests/test_app.py`](../tests/test_app.py) - Existing test suite

---

**Sprint Plan Prepared By:** GitHub Copilot  
**Review Required:** Product Owner sign-off before Sprint 0 starts
