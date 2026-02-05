#!/bin/bash
# ===========================================================================
# ProjektCoPilot — Veri Modeli Kurulum Script'i
# ===========================================================================
# Bu script'i Codespaces terminaline yapıştır.
# Mevcut dosyalara DOKUNMAZ, sadece yeni dosyalar ekler.
# ===========================================================================

set -e
echo "🚀 ProjektCoPilot veri modeli kurulumu başlıyor..."

# Proje kökünde olduğumuzu kontrol et
if [ ! -f "app.py" ]; then
    echo "⚠️  app.py bulunamadı. Proje kökünde olduğundan emin ol:"
    echo "    cd /workspaces/ProjektCoPilot"
    exit 1
fi

echo "✅ Proje kökü tespit edildi: $(pwd)"

# ---------------------------------------------------------------------------
# 1. .github/copilot-instructions.md — Copilot'un otomatik okuduğu dosya
# ---------------------------------------------------------------------------
mkdir -p .github
echo "📝 .github/copilot-instructions.md oluşturuluyor..."

cat > .github/copilot-instructions.md << 'COPILOT_EOF'
# ProjektCoPilot — Database Schema & Implementation Guide

> **Bu doküman GitHub Copilot için referans dokümanıdır.**
> Proje context'ine otomatik eklenir. Copilot tüm veri modelini, iş kurallarını
> ve ilişkileri anlayarak tutarlı kod üretir.

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     CORE LAYER (newreq.md)                  │
│                                                             │
│  PROJECT ──1:N──► SCENARIO ──1:N──► ANALYSIS ──1:N──► REQ  │
│                      │                                 │    │
│                      │                          ┌──────┴──┐ │
│                      │                     Fit──►CONFIG    │ │
│                      │                Gap/Part──►WRICEF    │ │
│                      │                          └──────┬──┘ │
├──────────────────────┼─────────────────────────────────┼────┤
│              TEST MANAGEMENT LAYER (Fonksiyonel)       │    │
│                      │                                 │    │
│                      ├──N:N──► TEST_CASE ◄──Convert────┘    │
│                                    │                        │
│  TEST_CYCLE ──1:N──► TEST_EXECUTION ◄──1:N── TEST_CASE     │
│                           │                                 │
│                      1:N──► DEFECT ──opt──► WRICEF          │
├─────────────────────────────────────────────────────────────┤
│                      AI LAYER (Entegrasyon)                 │
│                                                             │
│  AI_INTERACTION_LOG    (audit for all AI calls)             │
│  AI_EMBEDDINGS         (vector search / duplicate detect)   │
│  + ai_* columns on:    TEST_CASE (3 cols), DEFECT (8 cols)  │
└─────────────────────────────────────────────────────────────┘
```

**Tech Stack:** Flask + SQLAlchemy + SQLite (dev) / PostgreSQL (prod)

**Key Files:**
- `models.py` — SQLAlchemy model definitions (tüm entity'ler burada)
- `migration.sql` — Raw SQL (alternatif DB oluşturma)
- `app.py` — Flask routes ve API endpoints
- `templates/index.html` — Frontend (Fiori Horizon UI)

---

## 2. Entity Summary (12 tables + 1 bridge)

| # | Table | Layer | Code Prefix | Key Relationships |
|---|-------|-------|-------------|-------------------|
| 1 | `project` | Core | PRJ- | Root entity. 1:N to all others |
| 2 | `scenario` | Core | SCN- | N:1 project, 1:N analysis, self-ref parent |
| 3 | `analysis` | Core | ANL- | N:1 scenario, 1:N requirement |
| 4 | `requirement` | Core | REQ- | N:1 analysis. **SSOT for Fit-Gap** |
| 5 | `wricef_item` | Core | WR- | N:1 project, 0..1:1 requirement |
| 6 | `config_item` | Core | CFG- | N:1 project, 0..1:1 requirement |
| 7 | `test_case` | Test | TST- | N:1 project, polymorphic source |
| 8 | `test_cycle` | Test | CYC- | N:1 project, 1:N execution |
| 9 | `test_execution` | Test | EXE- | N:1 test_case, N:1 test_cycle |
| 10 | `defect` | Test | DEF- | N:1 execution, opt N:1 wricef |
| 11 | `ai_interaction_log` | AI | — | Polymorphic entity ref |
| 12 | `ai_embedding` | AI | — | Polymorphic entity ref |
| — | `scenario_test_case` | Bridge | — | N:N scenario↔test_case |

---

## 3. Critical Business Rules

### 3.1. SSOT Principle (Fit-Gap)
```
requirement.classification = 'Fit'        → Convert to CONFIG_ITEM
requirement.classification = 'PartialFit' → Convert to WRICEF_ITEM
requirement.classification = 'Gap'        → Convert to WRICEF_ITEM
```
**There is NO separate "FitGap" entity.** The classification lives on `requirement`.

When converting:
1. Create the target entity (WricefItem or ConfigItem)
2. Set `requirement.conversion_status` = 'WRICEF' or 'CONFIG'
3. Set `requirement.converted_item_id` = new item's ID
4. Set `requirement.converted_item_type` = 'WRICEF' or 'CONFIG'
5. Set `requirement.converted_at` and `converted_by`

### 3.2. Test Case Source Tracking (Polymorphic)
```python
test_case.source_type = 'WRICEF'    → source_id = wricef_item.id
test_case.source_type = 'CONFIG'    → source_id = config_item.id
test_case.source_type = 'SCENARIO'  → source_id = scenario.id
test_case.source_type = 'COMPOSITE' → source_id = NULL (manual assembly)
```

### 3.3. Defect Binding
```
Defect → test_execution (NOT test_case)
```
A defect is linked to a specific execution run, not the test case itself.
Optional: `defect.wricef_id` links to the development item.

### 3.4. Defect SLA Matrix
```
Critical + Urgent → 4 hours
Major    + High   → 8 hours
Minor    + Medium → 24 hours
Trivial  + Low    → 48 hours
```

### 3.5. Defect Lifecycle
```
NEW → OPEN → ASSIGNED → IN_PROGRESS → FIXED → RETEST → VERIFIED → CLOSED
                                                   └──→ REJECTED
```

### 3.6. Test Cycle Entry/Exit Criteria
```json
[
  {"criterion": "Tüm unit testler pass", "met": true},
  {"criterion": "Test ortamı hazır", "met": false}
]
```

### 3.7. Code Generation
All entities: `PREFIX-NNN` (DEF-001, DEF-002, ...)
```python
from models import generate_code, Defect
new_code = generate_code(Defect, project_id, 'DEF')
```

---

## 4. API Route Patterns

### 4.1. Core CRUD
```
GET/POST    /api/projects
GET/PUT/DEL /api/projects/<id>
GET/POST    /api/projects/<pid>/scenarios
GET/PUT/DEL /api/scenarios/<id>
GET/POST    /api/scenarios/<sid>/analyses
GET/PUT/DEL /api/analyses/<id>
GET/POST    /api/analyses/<aid>/requirements
GET/PUT/DEL /api/requirements/<id>
POST        /api/requirements/<id>/convert        ← Convert to WRICEF or CONFIG
GET/POST    /api/projects/<pid>/wricef-items
GET/POST    /api/projects/<pid>/config-items
```

### 4.2. Test Management
```
GET/POST    /api/projects/<pid>/test-cases
GET/POST    /api/projects/<pid>/test-cycles
GET/POST    /api/test-cycles/<cid>/executions
POST        /api/test-executions/<id>/report-defect
POST        /api/wricef-items/<id>/generate-test   ← steps → test case
POST        /api/config-items/<id>/generate-test
GET/POST    /api/projects/<pid>/defects
```

### 4.3. AI Layer
```
POST        /api/ai/chat
POST        /api/ai/generate-test-cases
POST        /api/ai/analyze-defect
POST        /api/ai/find-similar-defects
```

---

## 5. JSON Field Schemas

### test_case.steps / unit_test_steps
```json
[{"step_no":1, "action":"T-code XK01'i aç", "input":"Vendor Type: Domestic", "expected":"Vendor master açılır", "actual":""}]
```

### test_execution.step_results
```json
[{"step_no":1, "status":"Passed", "actual":"Başarılı", "screenshot_url":null}]
```

### test_execution.evidence
```json
[{"type":"screenshot", "url":"/uploads/exe-001.png", "caption":"Hata ekranı"}]
```

### defect.ai_similar_defects
```json
[{"defect_id":5, "defect_code":"DEF-005", "similarity":0.92, "title":"Aynı vendor hatası"}]
```

### config_item.config_details
```json
{"sscui":"100001", "path":"SPRO > FI > GL > Master Records", "parameters":[{"param":"Company Code","value":"1000"}]}
```

---

## 6. Enum Values

```python
PROJECT_STATUSES    = ['Active', 'Closed', 'OnHold']
PROJECT_PHASES      = ['Discover', 'Prepare', 'Explore', 'Realize', 'Deploy', 'Run']
SCENARIO_LEVELS     = ['L0', 'L1', 'L2', 'L3', 'L4', 'L5']
CLASSIFICATIONS     = ['Fit', 'PartialFit', 'Gap']
PRIORITIES          = ['Must', 'Should', 'Could', 'WontHave']
WRICEF_TYPES        = ['W', 'R', 'I', 'C', 'E', 'F']
SAP_MODULES         = ['FI','CO','SD','MM','PP','PM','QM','WM','EWM','HR','PS','ABAP','BASIS']
TEST_TYPES          = ['Unit','String','SIT','UAT','Sprint','Performance','Regression']
TEST_CASE_STATUSES  = ['Draft','Ready','Passed','Failed','Blocked','Deferred']
EXECUTION_STATUSES  = ['NotStarted','InProgress','Passed','Failed','Blocked']
CYCLE_STATUSES      = ['Planned','Active','Completed','Cancelled']
SEVERITIES          = ['Critical','Major','Minor','Trivial']
DEFECT_PRIORITIES   = ['Urgent','High','Medium','Low']
DEFECT_STATUSES     = ['New','Open','Assigned','InProgress','Fixed','Retest','Verified','Closed','Rejected']
ROOT_CAUSES         = ['Code','Config','Data','Requirement','Environment','ThirdParty','Unknown']
```

---

## 7. Convert Flow Implementation

### Requirement → WRICEF/CONFIG
```python
@app.route('/api/requirements/<int:req_id>/convert', methods=['POST'])
def convert_requirement(req_id):
    req = Requirement.query.get_or_404(req_id)
    if req.conversion_status != 'None':
        return jsonify(error='Already converted'), 400

    if req.classification == 'Fit':
        item = ConfigItem(project_id=..., requirement_id=req.id, ...)
        req.conversion_status = 'CONFIG'
    elif req.classification in ('Gap', 'PartialFit'):
        item = WricefItem(project_id=..., requirement_id=req.id, ...)
        req.conversion_status = 'WRICEF'

    db.session.add(item)
    db.session.flush()
    req.converted_item_id = item.id
    req.converted_item_type = req.conversion_status
    req.converted_at = datetime.utcnow()
    db.session.commit()
    return jsonify(id=item.id, code=item.code), 201
```

### WRICEF/CONFIG → Test Case
```python
@app.route('/api/wricef-items/<int:id>/generate-test', methods=['POST'])
def generate_test_from_wricef(id):
    wricef = WricefItem.query.get_or_404(id)
    tc = TestCase(
        project_id=wricef.project_id,
        code=generate_code(TestCase, wricef.project_id, 'TST'),
        test_type='Unit',
        title=f'Unit Test — {wricef.title}',
        source_type='WRICEF', source_id=wricef.id,
        steps=wricef.unit_test_steps
    )
    db.session.add(tc)
    db.session.commit()
    return jsonify(id=tc.id, code=tc.code), 201
```

---

## 8. Dashboard KPI Queries

### Test Progress per Cycle
```sql
SELECT tc.name, COUNT(te.id) AS total,
  SUM(CASE WHEN te.status='Passed' THEN 1 ELSE 0 END) AS passed,
  ROUND(100.0 * SUM(CASE WHEN te.status='Passed' THEN 1 ELSE 0 END) / NULLIF(COUNT(te.id),0), 1) AS pass_rate
FROM test_cycle tc LEFT JOIN test_execution te ON te.test_cycle_id = tc.id
WHERE tc.project_id = :pid GROUP BY tc.id;
```

### Open Defects by Severity
```sql
SELECT severity, COUNT(*) AS count,
  SUM(CASE WHEN sla_breached=1 THEN 1 ELSE 0 END) AS breached
FROM defect WHERE project_id = :pid AND status NOT IN ('Closed','Rejected','Verified')
GROUP BY severity;
```

---

## 9. Implementation Checklist

- [ ] `models.py` → Flask-SQLAlchemy modelleri (HAZIR)
- [ ] `migration.sql` → DB oluşturma (HAZIR)
- [ ] CRUD API endpoints (Section 4)
- [ ] Convert Flow: Requirement → WRICEF/CONFIG (Section 7)
- [ ] Convert Flow: WRICEF/CONFIG → TestCase (Section 7)
- [ ] TestExecution → Defect with SLA calculation
- [ ] TestCycle entry/exit criteria check
- [ ] Defect lifecycle state machine
- [ ] Auto code generation (generate_code helper)
- [ ] Dashboard KPI queries (Section 8)
- [ ] AI integration endpoints (Phase 2)
COPILOT_EOF

echo "✅ .github/copilot-instructions.md oluşturuldu"

# ---------------------------------------------------------------------------
# 2. docs/ klasörü — Dokümantasyon referansları
# ---------------------------------------------------------------------------
mkdir -p docs
echo "📁 docs/ klasörü oluşturuldu"

# Migration SQL'i docs'a koy (referans amaçlı, çalışan kod değil)
echo "📝 docs/migration.sql taşınıyor..."

cat > docs/migration.sql << 'SQL_EOF'
-- ===========================================================================
-- ProjektCoPilot — Database Migration Script
-- ===========================================================================
-- Kaynak: newreq.md + Fonksiyonel Tasarım + AI Entegrasyon Tasarımı
-- NOT: Bu dosya referans amaçlıdır. DB oluşturma models.py üzerinden yapılır.
--      Doğrudan SQL gerekirse bu script kullanılabilir.
-- ===========================================================================

CREATE TABLE IF NOT EXISTS project (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'Active',
    phase VARCHAR(20),
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scenario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    level VARCHAR(5),
    tags TEXT,
    is_composite BOOLEAN NOT NULL DEFAULT 0,
    included_scenario_ids JSON,
    parent_scenario_id INTEGER REFERENCES scenario(id),
    sort_order INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'Draft',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, code)
);
CREATE INDEX IF NOT EXISTS ix_scenario_project ON scenario(project_id);

CREATE TABLE IF NOT EXISTS analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_id INTEGER NOT NULL REFERENCES scenario(id) ON DELETE CASCADE,
    code VARCHAR(20) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    owner VARCHAR(50),
    status VARCHAR(20) DEFAULT 'Draft',
    workshop_date DATE,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_analysis_scenario ON analysis(scenario_id);

CREATE TABLE IF NOT EXISTS requirement (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER NOT NULL REFERENCES analysis(id) ON DELETE CASCADE,
    code VARCHAR(20) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    classification VARCHAR(20),
    priority VARCHAR(20),
    acceptance_criteria TEXT,
    conversion_status VARCHAR(20) NOT NULL DEFAULT 'None',
    converted_item_id INTEGER,
    converted_item_type VARCHAR(20),
    converted_at TIMESTAMP,
    converted_by VARCHAR(50),
    status VARCHAR(20) DEFAULT 'Draft',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_requirement_analysis ON requirement(analysis_id);
CREATE INDEX IF NOT EXISTS ix_requirement_classification ON requirement(classification);

CREATE TABLE IF NOT EXISTS wricef_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    scenario_id INTEGER REFERENCES scenario(id) ON DELETE SET NULL,
    requirement_id INTEGER REFERENCES requirement(id) ON DELETE SET NULL,
    code VARCHAR(20) NOT NULL,
    wricef_type VARCHAR(5) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    module VARCHAR(20),
    status VARCHAR(30) NOT NULL DEFAULT 'Backlog',
    owner VARCHAR(50),
    complexity VARCHAR(20),
    estimated_effort_days REAL,
    fs_content TEXT,
    ts_content TEXT,
    unit_test_steps JSON,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, code)
);
CREATE INDEX IF NOT EXISTS ix_wricef_project ON wricef_item(project_id);
CREATE INDEX IF NOT EXISTS ix_wricef_requirement ON wricef_item(requirement_id);

CREATE TABLE IF NOT EXISTS config_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    scenario_id INTEGER REFERENCES scenario(id) ON DELETE SET NULL,
    requirement_id INTEGER REFERENCES requirement(id) ON DELETE SET NULL,
    code VARCHAR(20) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    module VARCHAR(20),
    config_details JSON,
    unit_test_steps JSON,
    status VARCHAR(20) NOT NULL DEFAULT 'Draft',
    owner VARCHAR(50),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, code)
);
CREATE INDEX IF NOT EXISTS ix_config_project ON config_item(project_id);
CREATE INDEX IF NOT EXISTS ix_config_requirement ON config_item(requirement_id);

CREATE TABLE IF NOT EXISTS test_case (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    code VARCHAR(20) NOT NULL,
    test_type VARCHAR(20) NOT NULL,
    title VARCHAR(300) NOT NULL,
    description TEXT,
    module VARCHAR(20),
    status VARCHAR(20) NOT NULL DEFAULT 'Draft',
    owner VARCHAR(50),
    source_type VARCHAR(20),
    source_id INTEGER,
    steps JSON,
    priority VARCHAR(20),
    preconditions TEXT,
    automation_status VARCHAR(20) DEFAULT 'Manual',
    ai_generated BOOLEAN NOT NULL DEFAULT 0,
    ai_confidence_score REAL,
    risk_score REAL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, code)
);
CREATE INDEX IF NOT EXISTS ix_testcase_project ON test_case(project_id);
CREATE INDEX IF NOT EXISTS ix_testcase_type_status ON test_case(test_type, status);
CREATE INDEX IF NOT EXISTS ix_testcase_source ON test_case(source_type, source_id);

CREATE TABLE IF NOT EXISTS test_cycle (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(200) NOT NULL,
    test_type VARCHAR(20) NOT NULL,
    start_date DATE,
    end_date DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'Planned',
    entry_criteria JSON,
    entry_criteria_met BOOLEAN NOT NULL DEFAULT 0,
    exit_criteria JSON,
    exit_criteria_met BOOLEAN NOT NULL DEFAULT 0,
    target_pass_rate REAL,
    target_defect_density REAL,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, code)
);
CREATE INDEX IF NOT EXISTS ix_testcycle_project ON test_cycle(project_id);

CREATE TABLE IF NOT EXISTS test_execution (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_case_id INTEGER NOT NULL REFERENCES test_case(id) ON DELETE CASCADE,
    test_cycle_id INTEGER NOT NULL REFERENCES test_cycle(id) ON DELETE CASCADE,
    code VARCHAR(20) NOT NULL,
    tester VARCHAR(50),
    status VARCHAR(20) NOT NULL DEFAULT 'NotStarted',
    execution_date TIMESTAMP,
    duration_minutes INTEGER,
    evidence JSON,
    step_results JSON,
    notes TEXT,
    environment VARCHAR(20),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_execution_case_cycle ON test_execution(test_case_id, test_cycle_id);

CREATE TABLE IF NOT EXISTS defect (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    code VARCHAR(20) NOT NULL,
    title VARCHAR(300) NOT NULL,
    description TEXT,
    steps_to_reproduce TEXT,
    severity VARCHAR(20),
    priority VARCHAR(20),
    status VARCHAR(20) NOT NULL DEFAULT 'New',
    test_execution_id INTEGER REFERENCES test_execution(id) ON DELETE SET NULL,
    wricef_id INTEGER REFERENCES wricef_item(id) ON DELETE SET NULL,
    assigned_to VARCHAR(50),
    assigned_at TIMESTAMP,
    root_cause VARCHAR(20),
    root_cause_detail TEXT,
    resolution TEXT,
    resolved_at TIMESTAMP,
    sla_deadline TIMESTAMP,
    sla_breached BOOLEAN NOT NULL DEFAULT 0,
    ai_suggested_severity VARCHAR(20),
    ai_severity_confidence REAL,
    ai_root_cause_prediction VARCHAR(20),
    ai_root_cause_confidence REAL,
    ai_similar_defects JSON,
    ai_is_duplicate BOOLEAN,
    ai_duplicate_of_id INTEGER,
    ai_anomaly_flag BOOLEAN NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, code)
);
CREATE INDEX IF NOT EXISTS ix_defect_project ON defect(project_id);
CREATE INDEX IF NOT EXISTS ix_defect_execution ON defect(test_execution_id);
CREATE INDEX IF NOT EXISTS ix_defect_wricef ON defect(wricef_id);
CREATE INDEX IF NOT EXISTS ix_defect_severity_status ON defect(severity, status);

CREATE TABLE IF NOT EXISTS ai_interaction_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(50),
    session_id VARCHAR(100),
    interaction_type VARCHAR(30) NOT NULL,
    related_entity_type VARCHAR(30),
    related_entity_id INTEGER,
    input_text TEXT,
    output_text TEXT,
    model_used VARCHAR(50),
    tokens_in INTEGER,
    tokens_out INTEGER,
    cost_usd REAL,
    user_feedback VARCHAR(20),
    feedback_comment TEXT,
    response_time_ms INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_ai_type_date ON ai_interaction_log(interaction_type, created_at);

CREATE TABLE IF NOT EXISTS ai_embedding (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type VARCHAR(30) NOT NULL,
    entity_id INTEGER NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    embedding_vector JSON NOT NULL,
    metadata JSON,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entity_type, entity_id, content_hash)
);
CREATE INDEX IF NOT EXISTS ix_embedding_entity ON ai_embedding(entity_type, entity_id);

CREATE TABLE IF NOT EXISTS scenario_test_case (
    scenario_id INTEGER NOT NULL REFERENCES scenario(id) ON DELETE CASCADE,
    test_case_id INTEGER NOT NULL REFERENCES test_case(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (scenario_id, test_case_id)
);
SQL_EOF

echo "✅ docs/migration.sql oluşturuldu"

# ---------------------------------------------------------------------------
# 3. models.py — SQLAlchemy modelleri (app.py'nin import edeceği asıl dosya)
# ---------------------------------------------------------------------------

# Mevcut models.py varsa yedekle
if [ -f "models.py" ]; then
    cp models.py "models.py.backup_$(date +%Y%m%d_%H%M%S)"
    echo "⚠️  Mevcut models.py yedeklendi"
fi

echo "📝 models.py oluşturuluyor..."

cat > models.py << 'MODELS_EOF'
"""
ProjektCoPilot — Birleştirilmiş Veri Modeli (SQLAlchemy)
=========================================================
Kaynak: newreq.md + Fonksiyonel Tasarım + AI Entegrasyon Tasarımı

Katmanlar:
  CORE : Project → Scenario → Analysis → Requirement → WRICEF/Config
  TEST : TestCase → TestExecution → Defect, TestCycle
  AI   : AIInteractionLog, AIEmbedding + mevcut tablolara eklenen AI kolonları

Kullanım:
  from models import db, Project, Scenario, Analysis, Requirement, ...
  db.init_app(app)
  db.create_all()
"""

from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# ===========================================================================
# ENUMS
# ===========================================================================

PROJECT_STATUSES = ['Active', 'Closed', 'OnHold']
PROJECT_PHASES = ['Discover', 'Prepare', 'Explore', 'Realize', 'Deploy', 'Run']
SCENARIO_LEVELS = ['L0', 'L1', 'L2', 'L3', 'L4', 'L5']
CLASSIFICATIONS = ['Fit', 'PartialFit', 'Gap']
PRIORITIES = ['Must', 'Should', 'Could', 'WontHave']
CONVERSION_STATUSES = ['None', 'WRICEF', 'CONFIG']
WRICEF_TYPES = ['W', 'R', 'I', 'C', 'E', 'F']
SAP_MODULES = ['FI', 'CO', 'SD', 'MM', 'PP', 'PM', 'QM', 'WM', 'EWM',
               'HR', 'PS', 'CS', 'FICO', 'ABAP', 'BASIS', 'BW', 'BRIM',
               'TM', 'GTS', 'EHS', 'IS-OIL', 'IS-CHEM', 'CROSS']
DEV_STATUSES = ['Backlog', 'InDesign', 'InDevelopment', 'UnitTesting', 'ReadyForSIT', 'Done']
TEST_TYPES = ['Unit', 'String', 'SIT', 'UAT', 'Sprint', 'Performance', 'Regression']
TEST_CASE_STATUSES = ['Draft', 'Ready', 'Passed', 'Failed', 'Blocked', 'Deferred']
AUTOMATION_STATUSES = ['Manual', 'Automated', 'Candidate']
TEST_SOURCE_TYPES = ['WRICEF', 'CONFIG', 'SCENARIO', 'COMPOSITE']
EXECUTION_STATUSES = ['NotStarted', 'InProgress', 'Passed', 'Failed', 'Blocked']
ENVIRONMENTS = ['DEV', 'QA', 'PRE-PROD', 'PROD']
CYCLE_STATUSES = ['Planned', 'Active', 'Completed', 'Cancelled']
SEVERITIES = ['Critical', 'Major', 'Minor', 'Trivial']
DEFECT_PRIORITIES = ['Urgent', 'High', 'Medium', 'Low']
DEFECT_STATUSES = ['New', 'Open', 'Assigned', 'InProgress', 'Fixed', 'Retest', 'Verified', 'Closed', 'Rejected']
ROOT_CAUSES = ['Code', 'Config', 'Data', 'Requirement', 'Environment', 'ThirdParty', 'Unknown']
AI_INTERACTION_TYPES = ['Chat', 'Generation', 'Analysis', 'Prediction', 'AnomalyDetection']


# ===========================================================================
# CORE LAYER
# ===========================================================================

class Project(db.Model):
    __tablename__ = 'project'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='Active')
    phase = db.Column(db.String(20), nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    scenarios = db.relationship('Scenario', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    wricef_items = db.relationship('WricefItem', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    config_items = db.relationship('ConfigItem', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    test_cases = db.relationship('TestCase', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    test_cycles = db.relationship('TestCycle', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    defects = db.relationship('Defect', backref='project', lazy='dynamic', cascade='all, delete-orphan')


class Scenario(db.Model):
    __tablename__ = 'scenario'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id', ondelete='CASCADE'), nullable=False, index=True)
    code = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    level = db.Column(db.String(5), nullable=True)
    tags = db.Column(db.Text, nullable=True)
    is_composite = db.Column(db.Boolean, nullable=False, default=False)
    included_scenario_ids = db.Column(db.JSON, nullable=True)
    parent_scenario_id = db.Column(db.Integer, db.ForeignKey('scenario.id'), nullable=True)
    sort_order = db.Column(db.Integer, nullable=True, default=0)
    status = db.Column(db.String(20), nullable=True, default='Draft')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    analyses = db.relationship('Analysis', backref='scenario', lazy='dynamic', cascade='all, delete-orphan')
    children = db.relationship('Scenario', backref=db.backref('parent', remote_side='Scenario.id'), lazy='dynamic')

    __table_args__ = (db.UniqueConstraint('project_id', 'code', name='uq_scenario_project_code'),)


class Analysis(db.Model):
    __tablename__ = 'analysis'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    scenario_id = db.Column(db.Integer, db.ForeignKey('scenario.id', ondelete='CASCADE'), nullable=False, index=True)
    code = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    owner = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(20), nullable=True, default='Draft')
    workshop_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    requirements = db.relationship('Requirement', backref='analysis', lazy='dynamic', cascade='all, delete-orphan')


class Requirement(db.Model):
    """SSOT entity — classification alanı Fit-Gap kararını tutar."""
    __tablename__ = 'requirement'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey('analysis.id', ondelete='CASCADE'), nullable=False, index=True)
    code = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    classification = db.Column(db.String(20), nullable=True)  # Fit | PartialFit | Gap
    priority = db.Column(db.String(20), nullable=True)
    acceptance_criteria = db.Column(db.Text, nullable=True)
    conversion_status = db.Column(db.String(20), nullable=False, default='None')
    converted_item_id = db.Column(db.Integer, nullable=True)
    converted_item_type = db.Column(db.String(20), nullable=True)
    converted_at = db.Column(db.DateTime, nullable=True)
    converted_by = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(20), nullable=True, default='Draft')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    wricef_items = db.relationship('WricefItem', backref='requirement', lazy='dynamic')
    config_items = db.relationship('ConfigItem', backref='requirement', lazy='dynamic')


class WricefItem(db.Model):
    __tablename__ = 'wricef_item'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id', ondelete='CASCADE'), nullable=False, index=True)
    scenario_id = db.Column(db.Integer, db.ForeignKey('scenario.id', ondelete='SET NULL'), nullable=True)
    requirement_id = db.Column(db.Integer, db.ForeignKey('requirement.id', ondelete='SET NULL'), nullable=True, index=True)
    code = db.Column(db.String(20), nullable=False)
    wricef_type = db.Column(db.String(5), nullable=False)  # W/R/I/C/E/F
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    module = db.Column(db.String(20), nullable=True)
    status = db.Column(db.String(30), nullable=False, default='Backlog')
    owner = db.Column(db.String(50), nullable=True)
    complexity = db.Column(db.String(20), nullable=True)
    estimated_effort_days = db.Column(db.Float, nullable=True)
    fs_content = db.Column(db.Text, nullable=True)
    ts_content = db.Column(db.Text, nullable=True)
    unit_test_steps = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    defects = db.relationship('Defect', backref='wricef', lazy='dynamic')
    __table_args__ = (db.UniqueConstraint('project_id', 'code', name='uq_wricef_project_code'),)


class ConfigItem(db.Model):
    __tablename__ = 'config_item'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id', ondelete='CASCADE'), nullable=False, index=True)
    scenario_id = db.Column(db.Integer, db.ForeignKey('scenario.id', ondelete='SET NULL'), nullable=True)
    requirement_id = db.Column(db.Integer, db.ForeignKey('requirement.id', ondelete='SET NULL'), nullable=True, index=True)
    code = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    module = db.Column(db.String(20), nullable=True)
    config_details = db.Column(db.JSON, nullable=True)
    unit_test_steps = db.Column(db.JSON, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='Draft')
    owner = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('project_id', 'code', name='uq_config_project_code'),)


# ===========================================================================
# TEST MANAGEMENT LAYER
# ===========================================================================

class TestCase(db.Model):
    __tablename__ = 'test_case'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id', ondelete='CASCADE'), nullable=False, index=True)
    code = db.Column(db.String(20), nullable=False)
    test_type = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=True)
    module = db.Column(db.String(20), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='Draft')
    owner = db.Column(db.String(50), nullable=True)
    source_type = db.Column(db.String(20), nullable=True)
    source_id = db.Column(db.Integer, nullable=True)
    steps = db.Column(db.JSON, nullable=True)
    priority = db.Column(db.String(20), nullable=True)
    preconditions = db.Column(db.Text, nullable=True)
    automation_status = db.Column(db.String(20), nullable=True, default='Manual')
    # AI Layer
    ai_generated = db.Column(db.Boolean, nullable=False, default=False)
    ai_confidence_score = db.Column(db.Float, nullable=True)
    risk_score = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    executions = db.relationship('TestExecution', backref='test_case', lazy='dynamic', cascade='all, delete-orphan')
    __table_args__ = (
        db.UniqueConstraint('project_id', 'code', name='uq_testcase_project_code'),
        db.Index('ix_testcase_type_status', 'test_type', 'status'),
        db.Index('ix_testcase_source', 'source_type', 'source_id'),
    )


class TestCycle(db.Model):
    __tablename__ = 'test_cycle'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id', ondelete='CASCADE'), nullable=False, index=True)
    code = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    test_type = db.Column(db.String(20), nullable=False)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='Planned')
    entry_criteria = db.Column(db.JSON, nullable=True)
    entry_criteria_met = db.Column(db.Boolean, nullable=False, default=False)
    exit_criteria = db.Column(db.JSON, nullable=True)
    exit_criteria_met = db.Column(db.Boolean, nullable=False, default=False)
    target_pass_rate = db.Column(db.Float, nullable=True)
    target_defect_density = db.Column(db.Float, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    executions = db.relationship('TestExecution', backref='test_cycle', lazy='dynamic', cascade='all, delete-orphan')
    __table_args__ = (db.UniqueConstraint('project_id', 'code', name='uq_testcycle_project_code'),)


class TestExecution(db.Model):
    __tablename__ = 'test_execution'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    test_case_id = db.Column(db.Integer, db.ForeignKey('test_case.id', ondelete='CASCADE'), nullable=False, index=True)
    test_cycle_id = db.Column(db.Integer, db.ForeignKey('test_cycle.id', ondelete='CASCADE'), nullable=False, index=True)
    code = db.Column(db.String(20), nullable=False)
    tester = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='NotStarted')
    execution_date = db.Column(db.DateTime, nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True)
    evidence = db.Column(db.JSON, nullable=True)
    step_results = db.Column(db.JSON, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    environment = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    defects = db.relationship('Defect', backref='test_execution', lazy='dynamic', cascade='all, delete-orphan')
    __table_args__ = (db.Index('ix_execution_case_cycle', 'test_case_id', 'test_cycle_id'),)


class Defect(db.Model):
    __tablename__ = 'defect'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id', ondelete='CASCADE'), nullable=False, index=True)
    code = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=True)
    steps_to_reproduce = db.Column(db.Text, nullable=True)
    severity = db.Column(db.String(20), nullable=True)
    priority = db.Column(db.String(20), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='New')
    test_execution_id = db.Column(db.Integer, db.ForeignKey('test_execution.id', ondelete='SET NULL'), nullable=True, index=True)
    wricef_id = db.Column(db.Integer, db.ForeignKey('wricef_item.id', ondelete='SET NULL'), nullable=True, index=True)
    assigned_to = db.Column(db.String(50), nullable=True)
    assigned_at = db.Column(db.DateTime, nullable=True)
    root_cause = db.Column(db.String(20), nullable=True)
    root_cause_detail = db.Column(db.Text, nullable=True)
    resolution = db.Column(db.Text, nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    sla_deadline = db.Column(db.DateTime, nullable=True)
    sla_breached = db.Column(db.Boolean, nullable=False, default=False)
    # AI Layer
    ai_suggested_severity = db.Column(db.String(20), nullable=True)
    ai_severity_confidence = db.Column(db.Float, nullable=True)
    ai_root_cause_prediction = db.Column(db.String(20), nullable=True)
    ai_root_cause_confidence = db.Column(db.Float, nullable=True)
    ai_similar_defects = db.Column(db.JSON, nullable=True)
    ai_is_duplicate = db.Column(db.Boolean, nullable=True)
    ai_duplicate_of_id = db.Column(db.Integer, nullable=True)
    ai_anomaly_flag = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('project_id', 'code', name='uq_defect_project_code'),
        db.Index('ix_defect_severity_status', 'severity', 'status'),
    )


# ===========================================================================
# AI LAYER
# ===========================================================================

class AIInteractionLog(db.Model):
    __tablename__ = 'ai_interaction_log'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(50), nullable=True)
    session_id = db.Column(db.String(100), nullable=True)
    interaction_type = db.Column(db.String(30), nullable=False)
    related_entity_type = db.Column(db.String(30), nullable=True)
    related_entity_id = db.Column(db.Integer, nullable=True)
    input_text = db.Column(db.Text, nullable=True)
    output_text = db.Column(db.Text, nullable=True)
    model_used = db.Column(db.String(50), nullable=True)
    tokens_in = db.Column(db.Integer, nullable=True)
    tokens_out = db.Column(db.Integer, nullable=True)
    cost_usd = db.Column(db.Float, nullable=True)
    user_feedback = db.Column(db.String(20), nullable=True)
    feedback_comment = db.Column(db.Text, nullable=True)
    response_time_ms = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class AIEmbedding(db.Model):
    __tablename__ = 'ai_embedding'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    entity_type = db.Column(db.String(30), nullable=False)
    entity_id = db.Column(db.Integer, nullable=False)
    content_hash = db.Column(db.String(64), nullable=False)
    embedding_vector = db.Column(db.JSON, nullable=False)
    metadata = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('entity_type', 'entity_id', 'content_hash', name='uq_embedding_entity_hash'),
    )


# ===========================================================================
# BRIDGE TABLE — Scenario ↔ TestCase (N:N for SIT/UAT)
# ===========================================================================

scenario_test_case = db.Table(
    'scenario_test_case',
    db.Column('scenario_id', db.Integer, db.ForeignKey('scenario.id', ondelete='CASCADE'), primary_key=True),
    db.Column('test_case_id', db.Integer, db.ForeignKey('test_case.id', ondelete='CASCADE'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow),
)

Scenario.test_cases = db.relationship('TestCase', secondary=scenario_test_case,
                                       backref=db.backref('scenarios', lazy='dynamic'), lazy='dynamic')


# ===========================================================================
# HELPER — Auto Code Generator
# ===========================================================================

def generate_code(model_class, project_id, prefix):
    """Otomatik kod üretir: generate_code(Defect, 1, 'DEF') → 'DEF-042'"""
    last = model_class.query.filter_by(project_id=project_id).order_by(model_class.id.desc()).first()
    if last and last.code:
        try:
            num = int(last.code.split('-')[-1]) + 1
        except (ValueError, IndexError):
            num = 1
    else:
        num = 1
    return f'{prefix}-{num:03d}'


CODE_PREFIXES = {
    'Project': 'PRJ', 'Scenario': 'SCN', 'Analysis': 'ANL',
    'Requirement': 'REQ', 'WricefItem': 'WR', 'ConfigItem': 'CFG',
    'TestCase': 'TST', 'TestCycle': 'CYC', 'TestExecution': 'EXE', 'Defect': 'DEF',
}
MODELS_EOF

echo "✅ models.py oluşturuldu"

# ---------------------------------------------------------------------------
# 4. Flask-SQLAlchemy bağımlılığını kontrol et
# ---------------------------------------------------------------------------
echo "📦 Flask-SQLAlchemy kontrol ediliyor..."
pip install flask-sqlalchemy --quiet --break-system-packages 2>/dev/null || pip install flask-sqlalchemy --quiet 2>/dev/null
echo "✅ Flask-SQLAlchemy hazır"

# ---------------------------------------------------------------------------
# 5. Sonuç raporu
# ---------------------------------------------------------------------------
echo ""
echo "==========================================="
echo "🎉 KURULUM TAMAMLANDI!"
echo "==========================================="
echo ""
echo "📂 Oluşturulan dosyalar:"
echo ""
echo "  .github/"
echo "  └── copilot-instructions.md   ← Copilot bunu OTOMATİK okur"
echo ""
echo "  models.py                     ← SQLAlchemy modelleri (app.py import eder)"
echo ""
echo "  docs/"
echo "  └── migration.sql             ← SQL referans (opsiyonel)"
echo ""
echo "==========================================="
echo ""
echo "📌 SONRAKİ ADIMLAR:"
echo ""
echo "  1. app.py'de şu import'u ekle:"
echo "     from models import db, Project, Scenario, Analysis, Requirement, \\"
echo "         WricefItem, ConfigItem, TestCase, TestCycle, TestExecution, \\"
echo "         Defect, generate_code"
echo ""
echo "  2. app.py'de db'yi initialize et:"
echo "     app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///projektcopilot.db'"
echo "     db.init_app(app)"
echo "     with app.app_context():"
echo "         db.create_all()"
echo ""
echo "  3. Git commit yap:"
echo "     git add .github/copilot-instructions.md models.py docs/migration.sql"
echo "     git commit -m 'feat: add unified data model (3-layer schema)'"
echo "     git push"
echo ""
echo "  4. Copilot Chat'te test et:"
echo "     @workspace Create CRUD endpoints for TestCase entity"
echo ""
echo "==========================================="
