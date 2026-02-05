# 🚀 ProjektCoPilot - Master Development Plan

## 📋 Project Overview

**Proje Adı:** SAP AI Project Co-Pilot (ProjektCoPilot)  
**Amaç:** SAP S/4HANA transformation projelerini uçtan uca yönetmek için kapsamlı bir platform  
**Metodoloji:** SAP Activate  
**Versiyon:** 3.2  
**Last Updated:** 2026-02-05 19:00 (Code Quality + NewReq Migration)  
**Referans PRD:** newreq.md (Requirement-Centered Architecture)

---

## 🎉 LATEST UPDATES (2026-02-05 Evening)

### ✅ Code Quality Improvements
1. **Logging Infrastructure**
   - Added centralized logging with `logging` module
   - Error details logged server-side, generic messages to client
   - Exception stack traces captured for debugging

2. **Database Connection Management**
   - Implemented `db_conn()` context manager
   - Automatic connection cleanup in all code paths
   - Eliminated connection leak risks

3. **Input Validation**
   - Created `require_fields()` helper function
   - All POST/PUT endpoints validate required fields
   - Return 400 with missing field details

4. **Query Optimization**
   - Implemented DBConnProxy to rewrite `SELECT *` queries
   - Auto-converts to explicit column lists (23 tables mapped)
   - Improves performance and reduces breaking changes

5. **Test Coverage**
   - Added 17 comprehensive integration tests
   - All tests passing ✅ (pytest-flask)
   - Tests cover: Projects, Requirements, Sessions, Questions, Stats, Chat

6. **Environment Configuration**
   - `app.run()` now uses env vars (FLASK_HOST, FLASK_PORT, FLASK_DEBUG)
   - Safer production deployment
   - Identifier validation in auto_id generation

### ✅ NewReq Architecture Migration (Schema)
1. **Database Schema Updates**
   - Created migration script: `migrations/002_newreq_schema.sql`
   - Updated `database.py` with `run_migrations()` function
   
2. **Tables Updated**
   - `scenarios`: +3 columns (is_composite, included_scenario_ids, tags)
   - `new_requirements`: +3 columns (code, analysis_id, acceptance_criteria)
   - `wricef_items`: +4 columns (scenario_id, fs_link, ts_link, updated_at)
   - `config_items`: +2 columns (scenario_id, updated_at)

3. **New Tables**
   - `scenario_analyses`: Scenario → Analysis hierarchy support

4. **Backups Created**
   - Full project: `backups/working_version_20260205_113525.tar.gz`
   - Pre-migration DB: `backups/project_copilot_pre_newreq_20260205_115727.db`

### 📋 Next Steps (NewReq Implementation)
**Epic A: Backend API** (Ready to implement)
- [ ] Scenario CRUD with composite support
- [ ] Analysis CRUD (scenario-based)
- [ ] Requirement conversion endpoints (→ WRICEF/Config)
- [ ] WRICEF/Config → Unit Test conversion

**Epic B: Frontend UI** (Blocked by Epic A)
- [ ] Scenarios management screen
- [ ] Analysis management (under scenario)
- [ ] Requirements table (classification badges + convert buttons)
- [ ] Test Management 7-tab structure

---

## ⚠️ ROLLBACK NOTU (2026-02-05 Morning)

Sprint 1 (Phase 8: Legacy Cleanup) commit'i (`442eeec`) index.html'de JavaScript syntax
hataları oluşturdu (sed komutuyla comment kaldırma sırasında `//` prefix'i yanlış
silindi, script tag yapısı bozuldu). Uygulama tamamen çalışmaz hale geldi.

**Yapılan:** `git checkout 612636a -- templates/index.html app.py` ile Phase 3 commit'ine geri dönüldü.

**Kayıplar:**
- Phase 8 (Legacy Cleanup): 14 endpoint comment-out, 3 view comment-out — **GERİ ALINACAK**
- DB Fix: timeout=10, WAL mode, conn.close düzeltmeleri — **GERİ ALINACAK**
- Sprint 1'de eklenen yeni route'lar ve genişletilmiş database.py — **GERİ ALINACAK**

**Korunan:**
- Backup dosyaları diskte mevcut (`backups/`, `*.bak*` dosyaları)
- Sprint 1 commit git history'de mevcut (`442eeec`)
- database.py Sprint 1 versiyonu `git checkout 442eeec -- database.py` ile alınabilir
- Bozuk index.html yedeklendi: `templates/index.html.broken_sprint1`

---

## 🎯 Mimari Vizyon (newreq PRD)

```
PROJECT
    │
    ├── SCENARIO (O2C, P2P, R2R...)
    │       │
    │       └── ANALYSIS (Workshop / Breakdown)
    │               │
    │               └── REQUIREMENT (Fit / Partial Fit / Gap)
    │                       │
    │                       ├── [Fit] ──────► CONFIG_ITEM ──► Unit Test
    │                       └── [Gap/Partial] ► WRICEF_ITEM ──► FS/TS ──► Unit Test
    │
    ├── TEST MANAGEMENT
    │       ├── Unit Tests (WRICEF/Config kaynaklı)
    │       ├── SIT (Scenario bazlı)
    │       ├── UAT (Scenario/Composite bazlı)
    │       ├── String / Sprint / Performance / Regression
    │       │
    │       └── Traceability: Test ← source_type/source_id → WRICEF/Config/Scenario
    │
    └── SUPPORTING ENTITIES
            ├── Decisions, Risks, Actions, Attendees, Agenda, Minutes
            └── Audit Log
```

**Temel Prensip — SSOT = Requirement:**  
Fit/Partial Fit/Gap, requirement'ın classification'ıdır. Ayrı bir fitgap entity'si yaşamaz.

---

## 📊 Mevcut Teknik Durum (2026-02-05 19:00)

| Katman | Detay |
|--------|-------|
| **Backend** | app.py — Enhanced with logging, validation, db_conn context manager (~2100 satır) |
| **Database** | database.py — NewReq schema migrated (scenario_analyses, composite scenarios) |
| **Frontend** | index.html — Phase 3 seviyesi (~5800 satır), çalışıyor ✅ |
| **Tests** | test_app.py — 17 integration tests, all passing ✅ |
| **Git HEAD** | Updated with code quality improvements + schema migration |
| **Ortam** | GitHub Codespaces, Flask + SQLite + Vanilla JS + pytest |

### Key Files Status

| Dosya | Satır | Status | Son Değişiklik |
|-------|-------|--------|----------------|
| app.py | ~2100 | ✅ Production-ready | Code quality + proxy + logging |
| database.py | ~550 | ✅ NewReq-ready | Migration function added |
| test_app.py | ~250 | ✅ Comprehensive | 17 tests covering main APIs |
| newreq.md | ~300 | ✅ Reference | Architecture specification |
| MIGRATE_TO_SQLALCHEMY.md | - | 📋 Future | SQLAlchemy migration plan |

### Database Schema Alignment

| Entity (NewReq) | Table (Current) | Status |
|-----------------|-----------------|--------|
| PROJECT | projects | ✅ Tam uyumlu |
| SCENARIO | scenarios | ✅ Migrated (composite support added) |
| ANALYSIS | scenario_analyses | ✅ Yeni tablo oluşturuldu |
| REQUIREMENT | new_requirements | ✅ Enhanced (code, analysis_id, acceptance_criteria) |
| WRICEF_ITEM | wricef_items | ✅ Enhanced (scenario_id, links, updated_at) |
| CONFIG_ITEM | config_items | ✅ Enhanced (scenario_id, updated_at) |
| TEST_CASE | test_management | ✅ Tam uyumlu (source traceability mevcut) |

### Legacy Tables (Deprecation Planned)

| Tablo | Durum | Aksiyon |
|-------|-------|---------|
| fitgap | ⚠️ Legacy | Will be deprecated (use new_requirements.classification) |
| requirements | ⚠️ Legacy | Old WRICEF format (use new_requirements) |
| wricef | ⚠️ Legacy | Old format (use wricef_items) |
| analysis_sessions | ⚠️ Confusing name | Workshop sessions (keep for now, not same as scenario_analyses) |
| analyses | ⚠️ Wrong FK | Session-based (will be deprecated, use scenario_analyses) |

### Aktif Git Commit'ler

| Hash | Açıklama | Durum |
|------|----------|-------|
| `442eeec` | Sprint 1 Phase 8: Legacy cleanup | ❌ index.html bozuk, geri alındı |
| `308fe7e` | Fix: DB locking, WAL, conn.close | ⚠️ app.py geri alındı, tekrar uygulanacak |
| `612636a` | Phase 3: WRICEF API, Gap/Decision/Risk linking | ✅ **ŞU AN AKTİF** |
| `e163fa0` | Faz 1: Analysis DB genişletme | ✅ |
| `5df0554` | Task 2.4: Global Project Context | ✅ |

---

## ✅ Status Legend

| Simge | Anlam |
|-------|-------|
| ✅ | Tamamlandı ve çalışıyor |
| 🔄 | Devam ediyor |
| 📋 | Backlog (sırada) |
| ⚠️ | Kısmen mevcut, düzeltme/tamamlama gerekli |
| 🔙 | Yapılmıştı ama rollback'te kaybedildi — tekrar uygulanacak |
| ⸮ | Beklemede / İleride |

---

## PHASE 1: Foundation ✅ COMPLETED

| ID | Task | Status |
|----|------|--------|
| 1.1 | Flask backend (app.py) | ✅ |
| 1.2 | SQLite database (database.py) | ✅ |
| 1.3 | HTML/CSS frontend (index.html) | ✅ |
| 1.4 | Sidebar navigation | ✅ |
| 1.5 | Projects CRUD + detail | ✅ |
| 1.6 | Project cards grid | ✅ |
| 1.7 | Global project selector | ✅ |
| 1.8 | DB connection with WAL + timeout | 🔙 Rollback'te kayboldu |
| 1.9 | Auto-ID generator (generate_auto_id) | ✅ |

---

## PHASE 2: Analysis Workspace ✅ COMPLETED

| ID | Task | Status |
|----|------|--------|
| 2.1 | Sessions/Workshops CRUD | ✅ |
| 2.2 | Session detail (multi-tab) | ✅ |
| 2.3 | Q&A with status & auto-ID | ✅ |
| 2.4 | Fit-Gap analysis (legacy fitgap tablosu) | ✅ |
| 2.5 | Decisions with auto-ID | ✅ |
| 2.6 | Risks/Issues + risk score | ✅ |
| 2.7 | Actions with auto-ID | ✅ |
| 2.8 | Attendees, Agenda, Minutes | ✅ |
| 2.9 | Dashboard with stats API | ✅ |

---

## PHASE 3: Scenario & Entity Linking ⚠️ ACTIVE BASELINE

Bu phase şu an çalışan koddaki en son seviye.

| ID | Task | Status | Not |
|----|------|--------|-----|
| 3.1 | Scenarios table + CRUD API | ✅ | GET/POST/PUT/DELETE mevcut |
| 3.2 | Scenarios UI page (view-scenarios) | ✅ | Nav'da mevcut |
| 3.3 | Workshop → Scenario link (session.scenario_id) | ✅ | JOIN sorguları çalışıyor |
| 3.4 | Scenario auto-ID (S-001) | ✅ | |
| 3.5 | is_composite + included_scenario_ids alanları | 📋 | PRD gereksinimi — DB'ye eklenecek |
| 3.6 | Composite Scenario UI (multi-select) | 📋 | PRD gereksinimi |
| 3.7 | Gap ↔ Decision linking (related_decision_id) | ✅ | fitgap PUT'ta mevcut |
| 3.8 | Gap → WRICEF linking (related_wricef_id) | ✅ | fitgap PUT'ta mevcut |
| 3.9 | Risk → Scenario/Gap/WRICEF links | ⚠️ | PUT endpoint var ama UI kontrol edilmeli |

---

## PHASE 4: Requirement Refactor (EPIC-A) 🔙 NEEDS RE-IMPLEMENTATION

**Sprint 1'de yapılmıştı ama rollback'te kaybedildi.**

| ID | Task | Status | Not |
|----|------|--------|-----|
| 4.1 | new_requirements tablosu | 🔙 | database.py Sprint 1'den alınacak |
| 4.2 | new_requirements CRUD API | 🔙 | app.py Sprint 1'den cherry-pick edilecek |
| 4.3 | Requirement auto-code (REQ-001) | 📋 | |
| 4.4 | view-req-management UI sayfası | 🔙 | index.html'e temiz şekilde eklenecek |
| 4.5 | Classification badge (Fit/Partial Fit/Gap) | 📋 | |
| 4.6 | Classification bazlı filtreleme | 📋 | |
| 4.7 | Analysis sayfasında Requirements bölümü | 📋 | |
| 4.8 | analysis_id FK bağlantısı | 🔙 | |

---

## PHASE 5: Convert Flows (EPIC-B) 🔙 NEEDS RE-IMPLEMENTATION

| ID | Task | Status | Not |
|----|------|--------|-----|
| 5.1 | Convert API endpoint | 🔙 | Sprint 1 app.py'den alınacak |
| 5.2 | Already-converted kontrolü | 🔙 | |
| 5.3 | Fit → CONFIG_ITEM create | 🔙 | |
| 5.4 | Gap/PartialFit → WRICEF_ITEM create | 🔙 | |
| 5.5 | conversion_status/id/type/at/by güncelleme | 🔙 | |
| 5.6 | UI: Convert butonları | 📋 | |
| 5.7 | UI: "Open created item" linki | 📋 | |
| 5.8 | UI: Convert sonrası badge güncelleme | 📋 | |

---

## PHASE 6: WRICEF & Config Detail (EPIC-C) 🔙 PARTIALLY LOST

| ID | Task | Status | Not |
|----|------|--------|-----|
| 6.1 | wricef_items tablosu (PRD-uyumlu) | 🔙 | database.py Sprint 1'den alınacak |
| 6.2 | wricef_items CRUD API | 🔙 | |
| 6.3 | config_items tablosu (PRD-uyumlu) | 🔙 | |
| 6.4 | config_items CRUD API | 🔙 | |
| 6.5 | view-wricef-list UI sayfası | 🔙 | |
| 6.6 | view-config-list UI sayfası | 🔙 | |
| 6.7-6.16 | Detail UI + Convert to Test + Filters | 📋 / 🔙 | |

---

## PHASE 7: Test Management (EPIC-D) 🔙 PARTIALLY LOST

| ID | Task | Status | Not |
|----|------|--------|-----|
| 7.1 | test_management tablosu | 🔙 | database.py Sprint 1'den alınacak |
| 7.2 | test_management CRUD API | 🔙 | |
| 7.3 | 7 ayrı UI sayfası | 🔙 | |
| 7.4-7.10 | Detail views + filters | 📋 / 🔙 | |

---

## PHASE 8: Legacy Temizlik 🔙 NEEDS RE-IMPLEMENTATION

**Sprint 1'de tamamlanmıştı ama rollback'te kaybedildi.**

| ID | Task | Status | Not |
|----|------|--------|-----|
| 8.1-8.10 | Tüm legacy cleanup | 🔙 | Bu sefer index.html'i bozmadan yapılacak |

---

## PHASE 9-12: BACKLOG / FUTURE

Değişiklik yok — hâlâ backlog'da.

---

## 🎯 Kurtarma Planı (Recovery Strategy)

### Adım 1: Backend Kurtarma (app.py)
- Sprint 1 commit'inden (`442eeec`) app.py route'larını **cherry-pick** et
- DB fix'leri (timeout, WAL) tekrar uygula
- Legacy endpoint comment-out'ları tekrar yap
- **Test et:** API'ler 200 dönüyor mu?

### Adım 2: Database Kurtarma (database.py)
- Sprint 1 commit'inden database.py'yi al: `git checkout 442eeec -- database.py`
- `python -c "import database; database.init_db()"` çalıştır
- **Test et:** Yeni tablolar oluştu mu?

### Adım 3: Frontend Kurtarma (index.html) — DİKKATLİ
- Phase 3 çalışan index.html'i base olarak kullan
- Sprint 1'deki UI değişikliklerini **tek tek, test ederek** ekle
- Her ekleme sonrası browser'da kontrol et
- **ASLA toplu sed/replace kullanma**

### Adım 4: Commit & Test
- Temiz commit at
- Tam test suite çalıştır

---

## 📂 Mevcut Backup Dosyaları

| Dosya | İçerik | Kullanım |
|-------|--------|----------|
| `templates/index.html.broken_sprint1` | Bozuk Sprint 1 index.html | Referans — KULLANMA |
| `templates/index.html.bak` | Sprint 1 öncesi backup | Alternatif kaynak |
| `templates/index.html.backup_before_cleanup` | Legacy cleanup öncesi | Temiz referans |
| `backups/index.html.backup_20260204_124459` | 4 Şubat backup | Alternatif |
| `app.py.bak` / `app.py.bak2` / `app.py.bak3` | Sprint 1 app.py versiyonları | Route cherry-pick kaynağı |
| `backups/index_before_req_refactor.html` | Req refactor öncesi | Eski referans |

---

## 📁 Dosya Yapısı

```
/workspaces/ProjektCoPilot/
├── app.py                  # Flask backend (Phase 3 seviyesi)
├── database.py             # DB şeması (Phase 3 seviyesi)
├── project_copilot.db      # SQLite veritabanı
├── templates/
│   └── index.html          # Frontend (Phase 3, çalışıyor ✅)
├── backups/                # Çeşitli backup dosyaları
├── PROGRESS_REPORT.md      # Bu dosya
├── requirements.txt
└── README.md
```

---

## 💻 Geliştirme Ortamı

| Özellik | Detay |
|---------|-------|
| Platform | GitHub Codespaces |
| Backend | Python Flask 3.0.0 |
| Database | SQLite (newreq schema migrated) |
| Frontend | Vanilla HTML/CSS/JS + Jinja2 |
| Testing | pytest 7.4.3 + pytest-flask 1.3.0 |
| Port | 8080 (configurable via FLASK_PORT env) |
| Debug Mode | Off (use FLASK_DEBUG=true to enable) |
| Başlatma | `. .venv/bin/activate && python app.py` |
| Test | `. .venv/bin/activate && pytest test_app.py -v` |

---

## 🚀 Implementation Roadmap (NewReq Architecture)

### Phase 1: Backend API Foundation ✅ COMPLETED
- [x] Schema migration (scenarios, new_requirements, wricef_items, config_items)
- [x] scenario_analyses table creation
- [x] Code quality improvements (logging, validation, db context)
- [x] Test infrastructure (17 integration tests)
- [x] Backups and documentation

### Phase 2: Scenario & Analysis APIs 📋 NEXT
**Epic A1: Scenario Management**
- [ ] GET /api/scenarios?project_id=X (enhanced with composite info)
- [ ] POST /api/scenarios (with is_composite, included_scenario_ids, tags)
- [ ] PUT /api/scenarios/:id
- [ ] DELETE /api/scenarios/:id
- [ ] GET /api/scenarios/:id (detail with included scenarios expanded)

**Epic A2: Analysis Management**
- [ ] GET /api/analyses?scenario_id=X (scenario_analyses table)
- [ ] POST /api/analyses (with scenario_id, code auto-generation: ANL-001)
- [ ] PUT /api/analyses/:id
- [ ] DELETE /api/analyses/:id
- [ ] GET /api/analyses/:id

### Phase 3: Requirement Management & Conversion 📋
**Epic A3: Enhanced Requirements**
- [ ] GET /api/requirements?analysis_id=X (use new_requirements + new columns)
- [ ] POST /api/requirements (with code: REQ-001, classification validation)
- [ ] PUT /api/requirements/:id
- [ ] DELETE /api/requirements/:id
- [ ] Migrate existing new_requirements.session_id → analysis_id

**Epic B: Conversion Flows**
- [ ] POST /api/requirements/:id/convert (Fit→Config, Gap/Partial→WRICEF)
- [ ] Validation: classification-based target selection
- [ ] Update conversion_status, converted_item_type, converted_item_id
- [ ] Prevent duplicate conversions
- [ ] Add scenario_id to created WRICEF/Config items

### Phase 4: WRICEF & Config Enhancements 📋
**Epic C: Enhanced WRICEF/Config**
- [ ] Update GET /api/wricef to use new columns (scenario_id, fs_link, ts_link)
- [ ] Update GET /api/config to use new columns
- [ ] POST /api/wricef/:id/convert-to-unit-test
- [ ] POST /api/config/:id/convert-to-unit-test
- [ ] Create TEST_CASE with source_type, source_id traceability
- [ ] Copy unit_test_steps → test_management.steps (snapshot)

### Phase 5: Test Management Expansion 📋
**Epic D: 7-Tab Test Structure**
- [ ] GET /api/tests?test_type=Unit|SIT|UAT|String|Sprint|PerformanceLoad|Regression
- [ ] Update test_management UI for tab filtering
- [ ] SIT/UAT: scenario-based test case creation
- [ ] Composite scenario support for UAT tests
- [ ] Test execution tracking (future)

### Phase 6: Frontend UI Implementation 📋
- [ ] Scenarios management screen (composite scenario UI)
- [ ] Analysis screen (under scenario, tabbed view)
- [ ] Requirements table (classification badges, convert buttons)
- [ ] WRICEF detail (FS/TS links, unit steps editor)
- [ ] Config detail (config details, unit steps editor)
- [ ] Test Management 7-tab interface
- [ ] Traceability visualization (requirement → wricef/config → test)

### Phase 7: Data Migration & Cleanup 📋
- [ ] Migrate fitgap → new_requirements (classification='Gap')
- [ ] Migrate new_requirements.session_id → analysis_id
- [ ] Create default scenario_analyses from analysis_sessions
- [ ] Archive legacy tables (fitgap, requirements, wricef, analyses)
- [ ] Update all frontend references to new schemas

---

## 📈 Progress Metrics

### Code Quality
- ✅ Logging: Implemented
- ✅ Error handling: Standardized
- ✅ Input validation: 6 endpoints
- ✅ DB management: Context manager
- ✅ Query optimization: SELECT * proxy
- ✅ Test coverage: 17/17 passing

### Schema Alignment (NewReq)
- ✅ scenarios: 100% aligned
- ✅ scenario_analyses: Created
- ✅ new_requirements: 90% aligned (migration pending)
- ✅ wricef_items: 100% aligned
- ✅ config_items: 100% aligned
- ✅ test_management: 100% aligned

### API Completeness (NewReq)
- Projects: ✅ 100%
- Scenarios: ⚠️ 60% (need composite support)
- Analyses: ❌ 0% (new entity, needs implementation)
- Requirements: ⚠️ 40% (exists but needs enhancement)
- Conversion: ❌ 0% (needs implementation)
- WRICEF/Config: ⚠️ 70% (exists, needs unit test conversion)
- Test Management: ⚠️ 50% (exists, needs tab structure)

---

## 👥 Contributors
- **Umut Soyyılmaz** - Product Owner, SAP Expert
- **Claude AI** - Development Partner

---

*Last Updated: 2026-02-05 19:00 — Code Quality + NewReq Schema Migration*
