# ProjektCoPilot — Database Schema & Implementation Guide

> **Bu doküman GitHub Copilot (veya herhangi bir AI coding assistant) için referans dokümanıdır.**
> Proje context'ine eklendiğinde, Copilot tüm veri modelini, iş kurallarını ve ilişkileri anlayarak
> tutarlı kod üretebilir.

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
- `models.py` — SQLAlchemy model definitions (bu dosyayla birlikte kullan)
- `migration.sql` — Raw SQL for direct DB creation
- This guide — Business rules, relationships, API patterns

---

## 2. Entity Summary (12 tables)

| # | Table | Layer | PK | Code Prefix | Key Relationships |
|---|-------|-------|----|-------------|-------------------|
| 1 | `project` | Core | id | PRJ- | Root entity. 1:N to all others |
| 2 | `scenario` | Core | id | SCN- | N:1 project, 1:N analysis, self-ref parent |
| 3 | `analysis` | Core | id | ANL- | N:1 scenario, 1:N requirement |
| 4 | `requirement` | Core | id | REQ- | N:1 analysis. SSOT for Fit-Gap |
| 5 | `wricef_item` | Core | id | WR- | N:1 project, 0..1:1 requirement |
| 6 | `config_item` | Core | id | CFG- | N:1 project, 0..1:1 requirement |
| 7 | `test_case` | Test | id | TST- | N:1 project, polymorphic source |
| 8 | `test_cycle` | Test | id | CYC- | N:1 project, 1:N execution |
| 9 | `test_execution` | Test | id | EXE- | N:1 test_case, N:1 test_cycle |
| 10 | `defect` | Test | id | DEF- | N:1 execution, opt N:1 wricef |
| 11 | `ai_interaction_log` | AI | id | — | Polymorphic entity ref |
| 12 | `ai_embedding` | AI | id | — | Polymorphic entity ref |
| — | `scenario_test_case` | Bridge | composite | — | N:N scenario↔test_case |

---

## 3. Critical Business Rules

### 3.1. SSOT Principle (Fit-Gap)
```
requirement.classification  = 'Fit'        → Convert to CONFIG_ITEM
requirement.classification  = 'PartialFit' → Convert to WRICEF_ITEM
requirement.classification  = 'Gap'        → Convert to WRICEF_ITEM
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

Unit tests come from WRICEF/CONFIG `unit_test_steps` JSON.
SIT/UAT tests come from SCENARIO (via N:N bridge table `scenario_test_case`).

### 3.3. Defect Binding
```
Defect → test_execution (NOT test_case)
```
A defect is always linked to a specific execution run, not the test case itself. This is because the same test case can pass in one run and fail in another. The execution record captures the exact context (cycle, tester, environment, date).

Optional: `defect.wricef_id` links to the development item that caused the defect.

### 3.4. Defect SLA Matrix
```
severity=Critical + priority=Urgent  → SLA: 4 hours
severity=Major    + priority=High    → SLA: 8 hours
severity=Minor    + priority=Medium  → SLA: 24 hours
severity=Trivial  + priority=Low     → SLA: 48 hours
```
On defect creation, compute `sla_deadline` from `created_at + SLA duration`.
On each status update, check if `datetime.utcnow() > sla_deadline` → set `sla_breached = True`.

### 3.5. Defect Lifecycle
```
NEW → OPEN → ASSIGNED → IN_PROGRESS → FIXED → RETEST → VERIFIED → CLOSED
                                                   └──→ REJECTED (if not valid)
```

### 3.6. Test Cycle Entry/Exit Criteria
```json
// test_cycle.entry_criteria example:
[
  {"criterion": "Tüm unit testler pass", "met": true},
  {"criterion": "Test ortamı hazır", "met": true},
  {"criterion": "Test verileri yüklendi", "met": false}
]
```
`entry_criteria_met` = all criteria have `met: true`
`exit_criteria_met` = all criteria have `met: true`

### 3.7. Code Generation Pattern
All entities with a `code` field follow the pattern: `PREFIX-NNN`
```python
# Example: generate next defect code for project_id=1
last = Defect.query.filter_by(project_id=1).order_by(Defect.id.desc()).first()
next_num = int(last.code.split('-')[-1]) + 1 if last else 1
new_code = f'DEF-{next_num:03d}'  # DEF-001, DEF-002, ...
```

---

## 4. API Route Patterns

### 4.1. Core CRUD Hierarchy
```
GET/POST   /api/projects
GET/PUT/DEL /api/projects/<id>

GET/POST   /api/projects/<pid>/scenarios
GET/PUT/DEL /api/scenarios/<id>

GET/POST   /api/scenarios/<sid>/analyses
GET/PUT/DEL /api/analyses/<id>

GET/POST   /api/analyses/<aid>/requirements
GET/PUT/DEL /api/requirements/<id>
POST       /api/requirements/<id>/convert    ← Convert to WRICEF or CONFIG

GET/POST   /api/projects/<pid>/wricef-items
GET/PUT/DEL /api/wricef-items/<id>

GET/POST   /api/projects/<pid>/config-items
GET/PUT/DEL /api/config-items/<id>
```

### 4.2. Test Management Routes
```
GET/POST   /api/projects/<pid>/test-cases
GET/PUT/DEL /api/test-cases/<id>
POST       /api/wricef-items/<id>/generate-test    ← Convert steps to test case
POST       /api/config-items/<id>/generate-test     ← Convert steps to test case

GET/POST   /api/projects/<pid>/test-cycles
GET/PUT/DEL /api/test-cycles/<id>

GET/POST   /api/test-cycles/<cid>/executions
GET/PUT/DEL /api/test-executions/<id>
POST       /api/test-executions/<id>/run            ← Start execution

GET/POST   /api/projects/<pid>/defects
GET/PUT/DEL /api/defects/<id>
POST       /api/test-executions/<id>/report-defect  ← Create defect from execution
```

### 4.3. AI Layer Routes
```
POST       /api/ai/chat                    ← Conversational assistant
POST       /api/ai/generate-test-cases     ← AI test case generation
POST       /api/ai/analyze-defect          ← Defect severity/root cause prediction
POST       /api/ai/find-similar-defects    ← Vector similarity search
POST       /api/ai/predict-regression      ← Predictive test selection
GET        /api/ai/interactions            ← Audit log
```

---

## 5. JSON Field Schemas

### 5.1. test_case.steps / wricef_item.unit_test_steps / config_item.unit_test_steps
```json
[
  {
    "step_no": 1,
    "action": "T-code XK01'i aç",
    "input": "Vendor Type: Domestic",
    "expected": "Vendor master ekranı açılır",
    "actual": ""
  }
]
```

### 5.2. test_execution.step_results
```json
[
  {
    "step_no": 1,
    "status": "Passed",
    "actual": "Vendor master ekranı başarıyla açıldı",
    "screenshot_url": null
  }
]
```

### 5.3. test_execution.evidence
```json
[
  {"type": "screenshot", "url": "/uploads/exe-001-step3.png", "caption": "Hata ekranı"},
  {"type": "log", "url": "/uploads/exe-001-sap-log.txt", "caption": "SAP system log"}
]
```

### 5.4. defect.ai_similar_defects
```json
[
  {"defect_id": 5, "defect_code": "DEF-005", "similarity": 0.92, "title": "Aynı vendor hatası"},
  {"defect_id": 12, "defect_code": "DEF-012", "similarity": 0.85, "title": "Benzer yetki sorunu"}
]
```

### 5.5. config_item.config_details
```json
{
  "sscui": "100001",
  "path": "SPRO > Financial Accounting > General Ledger > Master Records",
  "parameters": [
    {"param": "Company Code", "value": "1000"},
    {"param": "Fiscal Year Variant", "value": "K4"}
  ],
  "transport": "DEVK900123"
}
```

### 5.6. test_cycle.entry_criteria / exit_criteria
```json
[
  {"criterion": "Tüm unit testler pass olmuş olmalı", "met": true},
  {"criterion": "Test ortamı transport edilmiş olmalı", "met": true},
  {"criterion": "Test verileri yüklenmiş olmalı", "met": false}
]
```

---

## 6. Convert Flow Implementation

### 6.1. Requirement → WRICEF/CONFIG
```python
@app.route('/api/requirements/<int:req_id>/convert', methods=['POST'])
def convert_requirement(req_id):
    req = Requirement.query.get_or_404(req_id)
    data = request.json

    if req.conversion_status != 'None':
        return jsonify(error='Already converted'), 400

    if req.classification == 'Fit':
        item = ConfigItem(
            project_id=req.analysis.scenario.project_id,
            scenario_id=req.analysis.scenario_id,
            requirement_id=req.id,
            code=generate_code(ConfigItem, project_id, 'CFG'),
            title=data.get('title', req.title),
            module=data.get('module'),
        )
        db.session.add(item)
        req.conversion_status = 'CONFIG'
        req.converted_item_type = 'CONFIG'
    elif req.classification in ('Gap', 'PartialFit'):
        item = WricefItem(
            project_id=req.analysis.scenario.project_id,
            scenario_id=req.analysis.scenario_id,
            requirement_id=req.id,
            code=generate_code(WricefItem, project_id, 'WR'),
            wricef_type=data.get('wricef_type', 'E'),
            title=data.get('title', req.title),
            module=data.get('module'),
        )
        db.session.add(item)
        req.conversion_status = 'WRICEF'
        req.converted_item_type = 'WRICEF'
    else:
        return jsonify(error='Classification must be set first'), 400

    db.session.flush()  # Get item.id
    req.converted_item_id = item.id
    req.converted_at = datetime.utcnow()
    req.converted_by = data.get('user', 'system')
    db.session.commit()

    return jsonify(id=item.id, code=item.code), 201
```

### 6.2. WRICEF/CONFIG → Test Case
```python
@app.route('/api/wricef-items/<int:wricef_id>/generate-test', methods=['POST'])
def generate_test_from_wricef(wricef_id):
    wricef = WricefItem.query.get_or_404(wricef_id)

    if not wricef.unit_test_steps:
        return jsonify(error='No unit_test_steps defined'), 400

    tc = TestCase(
        project_id=wricef.project_id,
        code=generate_code(TestCase, wricef.project_id, 'TST'),
        test_type='Unit',
        title=f'Unit Test — {wricef.title}',
        module=wricef.module,
        source_type='WRICEF',
        source_id=wricef.id,
        steps=wricef.unit_test_steps,
        priority='High',
    )
    db.session.add(tc)
    db.session.commit()

    return jsonify(id=tc.id, code=tc.code), 201
```

---

## 7. Dashboard KPI Queries

### 7.1. Test Progress per Cycle
```sql
SELECT
    tc.code AS cycle_code,
    tc.name AS cycle_name,
    COUNT(te.id) AS total_executions,
    SUM(CASE WHEN te.status = 'Passed' THEN 1 ELSE 0 END) AS passed,
    SUM(CASE WHEN te.status = 'Failed' THEN 1 ELSE 0 END) AS failed,
    SUM(CASE WHEN te.status = 'Blocked' THEN 1 ELSE 0 END) AS blocked,
    ROUND(100.0 * SUM(CASE WHEN te.status = 'Passed' THEN 1 ELSE 0 END) / NULLIF(COUNT(te.id), 0), 1) AS pass_rate
FROM test_cycle tc
LEFT JOIN test_execution te ON te.test_cycle_id = tc.id
WHERE tc.project_id = :project_id
GROUP BY tc.id
ORDER BY tc.start_date;
```

### 7.2. Open Defects by Severity
```sql
SELECT
    severity,
    COUNT(*) AS count,
    SUM(CASE WHEN sla_breached = 1 THEN 1 ELSE 0 END) AS sla_breached_count
FROM defect
WHERE project_id = :project_id AND status NOT IN ('Closed', 'Rejected', 'Verified')
GROUP BY severity
ORDER BY CASE severity
    WHEN 'Critical' THEN 1 WHEN 'Major' THEN 2 WHEN 'Minor' THEN 3 ELSE 4 END;
```

### 7.3. Requirement Conversion Progress
```sql
SELECT
    classification,
    COUNT(*) AS total,
    SUM(CASE WHEN conversion_status != 'None' THEN 1 ELSE 0 END) AS converted,
    ROUND(100.0 * SUM(CASE WHEN conversion_status != 'None' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) AS conversion_pct
FROM requirement r
JOIN analysis a ON r.analysis_id = a.id
JOIN scenario s ON a.scenario_id = s.id
WHERE s.project_id = :project_id
GROUP BY classification;
```

---

## 8. Enum Values Quick Reference

```python
# All enum values are stored as VARCHAR, validated in application layer

PROJECT_STATUSES    = ['Active', 'Closed', 'OnHold']
PROJECT_PHASES      = ['Discover', 'Prepare', 'Explore', 'Realize', 'Deploy', 'Run']
SCENARIO_LEVELS     = ['L0', 'L1', 'L2', 'L3', 'L4', 'L5']
CLASSIFICATIONS     = ['Fit', 'PartialFit', 'Gap']
PRIORITIES          = ['Must', 'Should', 'Could', 'WontHave']
WRICEF_TYPES        = ['W', 'R', 'I', 'C', 'E', 'F']
SAP_MODULES         = ['FI','CO','SD','MM','PP','PM','QM','WM','EWM','HR','PS','ABAP','BASIS']
TEST_TYPES          = ['Unit', 'String', 'SIT', 'UAT', 'Sprint', 'Performance', 'Regression']
TEST_CASE_STATUSES  = ['Draft', 'Ready', 'Passed', 'Failed', 'Blocked', 'Deferred']
EXECUTION_STATUSES  = ['NotStarted', 'InProgress', 'Passed', 'Failed', 'Blocked']
CYCLE_STATUSES      = ['Planned', 'Active', 'Completed', 'Cancelled']
SEVERITIES          = ['Critical', 'Major', 'Minor', 'Trivial']
DEFECT_PRIORITIES   = ['Urgent', 'High', 'Medium', 'Low']
DEFECT_STATUSES     = ['New','Open','Assigned','InProgress','Fixed','Retest','Verified','Closed','Rejected']
ROOT_CAUSES         = ['Code', 'Config', 'Data', 'Requirement', 'Environment', 'ThirdParty', 'Unknown']
AUTOMATION_STATUSES = ['Manual', 'Automated', 'Candidate']
```

---

## 9. Implementation Checklist

- [ ] `models.py` → Flask-SQLAlchemy modelleri (hazır)
- [ ] `migration.sql` → DB oluşturma (hazır)
- [ ] CRUD API endpoints (Section 4 pattern'larını takip et)
- [ ] Convert Flow: Requirement → WRICEF/CONFIG (Section 6.1)
- [ ] Convert Flow: WRICEF/CONFIG → TestCase (Section 6.2)
- [ ] TestExecution → Defect creation with SLA calculation
- [ ] TestCycle entry/exit criteria check logic
- [ ] Defect lifecycle state machine (valid transitions)
- [ ] Auto code generation (generate_code helper)
- [ ] Dashboard KPI queries (Section 7)
- [ ] AI integration endpoints (Phase 2)
- [ ] Vector embedding pipeline (Phase 3)
