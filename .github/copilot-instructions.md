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
