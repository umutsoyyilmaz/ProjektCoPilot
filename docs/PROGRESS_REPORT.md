# 🚀 ProjektCoPilot - Master Development Plan

## 📋 Project Overview

**Proje Adı:** SAP AI Project Co-Pilot (ProjektCoPilot)  
**Amaç:** SAP S/4HANA transformation projelerini uçtan uca yönetmek için kapsamlı bir platform  
**Metodoloji:** SAP Activate  
**Versiyon:** 3.0  
**Last Updated:** 2026-02-05  
**Referans PRD:** newreq.md (Requirement-Centered Architecture)

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

## 📊 Mevcut Teknik Durum

| Katman | Detay |
|--------|-------|
| **Backend** | app.py — 2058 satır, ~86 route |
| **Database** | database.py — 22 tablo (eski + yeni karışık) |
| **Frontend** | index.html — 7051 satır, 159 JS fonksiyon, 21 view |
| **Test** | Son çalıştırma: 95/102 pass |
| **Ortam** | GitHub Codespaces, Flask + SQLite + Vanilla JS |

### Mevcut Veritabanı Tabloları (22)

**PRD-uyumlu (aktif kullanılacak):**
```
projects, scenarios, analysis_sessions, new_requirements,
wricef_items, config_items, test_management,
session_attendees, session_agenda, meeting_minutes,
action_items, decisions, risks_issues, questions, answers,
analyses, audit_log
```

**Legacy (temizlenecek/devre dışı bırakılacak):**
```
requirements    → eski WRICEF-requirement tablosu, new_requirements ile karışıyor
fitgap          → ayrı entity olarak yaşıyor, PRD'ye göre kalkmalı
wricef          → legacy basit tablo, wricef_items ile çakışıyor
test_cases      → FS/TS dokümana bağlı eski yapı, test_management ile çakışıyor
fs_ts_documents → eski doküman yapısı (WRICEF item içine taşınacak)
```

---

## ✅ Status Legend

| Simge | Anlam |
|-------|-------|
| ✅ | Tamamlandı |
| 🔄 | Devam ediyor |
| 📋 | Backlog (sırada) |
| ⚠️ | Kısmen mevcut, düzeltme/tamamlama gerekli |
| 🗑️ | Legacy — temizlenecek |
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
| 1.8 | DB connection with WAL + timeout | ✅ |
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

## PHASE 3: Scenario & Entity Linking ⚠️ PARTIALLY DONE

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

## PHASE 4: Requirement Refactor (EPIC-A from newreq PRD) ⚠️ MOSTLY DONE

**Hedef:** fitgap entity'si yerine new_requirements tablosu SSOT olacak.

| ID | Task | Status | Not |
|----|------|--------|-----|
| 4.1 | new_requirements tablosu | ✅ | classification, conversion_status, converted_item_id/type/at/by alanları mevcut |
| 4.2 | new_requirements CRUD API | ✅ | /api/new-requirements — GET/POST/PUT/DELETE |
| 4.3 | Requirement auto-code (REQ-001) | ⚠️ | code alanı var ama auto-generate yok — eklenecek |
| 4.4 | view-req-management UI sayfası | ✅ | Nav'da "Requirements" olarak mevcut |
| 4.5 | Classification badge (Fit/Partial Fit/Gap) | ⚠️ | UI'da kontrol edilmeli — PRD'deki badge + filtre |
| 4.6 | Classification bazlı filtreleme | ⚠️ | UI'da kontrol edilmeli |
| 4.7 | Analysis sayfasında Requirements bölümü | ⚠️ | Eski "Fit-Gap" label → "Requirements" rename kontrol edilmeli |
| 4.8 | analysis_id FK bağlantısı | ✅ | new_requirements.analysis_id mevcut |

---

## PHASE 5: Convert Flows (EPIC-B from newreq PRD) ✅ BACKEND DONE, UI TBD

**Hedef:** Requirement → WRICEF/Config dönüşüm akışı.

| ID | Task | Status | Not |
|----|------|--------|-----|
| 5.1 | Convert API endpoint | ✅ | POST /api/new-requirements/<id>/convert — Fit→Config, Gap/Partial→WRICEF |
| 5.2 | Already-converted kontrolü | ✅ | conversion_status != 'None' check |
| 5.3 | Fit → CONFIG_ITEM create | ✅ | config_items tablosuna INSERT |
| 5.4 | Gap/PartialFit → WRICEF_ITEM create | ✅ | wricef_items tablosuna INSERT |
| 5.5 | conversion_status/id/type/at/by güncelleme | ✅ | |
| 5.6 | UI: Convert butonlarının koşullu gösterimi | 📋 | Fit → sadece "Convert to Config", Gap/Partial → sadece "Convert to WRICEF" |
| 5.7 | UI: "Open created item" linki | 📋 | Requirement satırında convert edilen item'a link |
| 5.8 | UI: Convert sonrası badge güncelleme | 📋 | Conversion Status badge (None/WRICEF/CONFIG) |

---

## PHASE 6: WRICEF & Config Detail (EPIC-C from newreq PRD) ⚠️ MOSTLY DONE

**Hedef:** WRICEF/Config item detail sayfaları + Unit Test dönüşümü.

| ID | Task | Status | Not |
|----|------|--------|-----|
| 6.1 | wricef_items tablosu (PRD-uyumlu) | ✅ | fs_content, ts_content, unit_test_steps alanları mevcut |
| 6.2 | wricef_items CRUD API | ✅ | GET/POST/PUT/DELETE + GET by id |
| 6.3 | config_items tablosu (PRD-uyumlu) | ✅ | config_details, unit_test_steps alanları mevcut |
| 6.4 | config_items CRUD API | ✅ | GET/POST/PUT/DELETE + GET by id |
| 6.5 | view-wricef-list UI sayfası | ✅ | Nav'da mevcut |
| 6.6 | view-config-list UI sayfası | ✅ | Nav'da mevcut |
| 6.7 | WRICEF detail: FS/TS editor UI | ⚠️ | Backend hazır, UI kalitesi kontrol edilmeli |
| 6.8 | WRICEF detail: Unit Test Steps editor UI | ⚠️ | JSON array olarak tutuluyor, UI editor kalitesi kontrol edilmeli |
| 6.9 | Config detail: Config Details editor UI | ⚠️ | Backend hazır, UI kontrol edilmeli |
| 6.10 | Config detail: Unit Test Steps editor UI | ⚠️ | Aynı durum |
| 6.11 | Convert to Unit Test API (WRICEF) | ✅ | POST /api/wricef-items/<id>/convert-to-test — steps boş kontrolü var |
| 6.12 | Convert to Unit Test API (Config) | ✅ | POST /api/config-items/<id>/convert-to-test — steps boş kontrolü var |
| 6.13 | UI: "Convert to Unit Test" butonu | ⚠️ | Kontrol edilmeli — buton görünürlüğü + tıklama sonrası feedback |
| 6.14 | UI: "Created Unit Test: UT-xxx" linki | 📋 | Item detail'de oluşturulan test'e link |
| 6.15 | Source traceability (test → WRICEF/Config) | ✅ | test_management.source_type + source_id |
| 6.16 | WRICEF filtre: type, status, module, scenario, requirement | ⚠️ | API'de project_id filtresi var, diğerleri kontrol edilmeli |

---

## PHASE 7: Test Management (EPIC-D from newreq PRD) ⚠️ SKELETON DONE

**Hedef:** 7 test türü için tab yapısı, source traceability, scenario linkage.

| ID | Task | Status | Not |
|----|------|--------|-----|
| 7.1 | test_management tablosu | ✅ | test_type, source_type, source_id, steps (JSON) |
| 7.2 | test_management CRUD API | ✅ | GET (test_type filtreli), POST, PUT, DELETE |
| 7.3 | 7 ayrı UI sayfası (Unit/SIT/UAT/String/Sprint/Perf/Regression) | ✅ | Nav'da 7 ayrı link, 7 ayrı view |
| 7.4 | Unit test listesi + detail | ⚠️ | İskelet var, steps gösterimi ve source trace UI kontrol edilmeli |
| 7.5 | SIT/UAT: Scenario referanslı model | 📋 | source_type=SCENARIO/COMPOSITE_SCENARIO — UI'da scenario seçimi yok |
| 7.6 | SIT/UAT: Composite scenario desteği | 📋 | Önce Phase 3.5-3.6 (is_composite) tamamlanmalı |
| 7.7 | Test detail: steps viewer/editor | ⚠️ | JSON steps gösterimi kontrol edilmeli |
| 7.8 | Test detail: execution status tracking | ⚠️ | Draft/Ready/Executed/Passed/Failed/Blocked — UI kontrol edilmeli |
| 7.9 | Test detail: evidence/attachments | 📋 | İleride |
| 7.10 | Test filtre: status, owner, scenario, source | ⚠️ | API'de filtreler var, UI kontrol edilmeli |

---

## PHASE 8: Legacy Temizlik ✅ COMPLETED

**Hedef:** Eski ve yeni tabloların çakışmasını gidermek, tek kaynak (new tables) kullanmak.

| ID | Task | Status | Not |
|----|------|--------|-----|
| 8.1 | requirements tablosu → devre dışı | ✅ | 2 endpoint comment out (GET, POST) |
| 8.2 | fitgap tablosu → devre dışı | ✅ | 4 endpoint comment out (GET list, POST, GET by id, PUT) |
| 8.3 | wricef (legacy) tablosu → devre dışı | ✅ | 5 endpoint comment out (full CRUD) |
| 8.4 | test_cases tablosu → devre dışı | ✅ | 3 endpoint comment out (GET, POST, PUT) |
| 8.5 | Legacy API route'larını kaldır/redirect | ✅ | 14 endpoint comment edildi |
| 8.6 | Legacy UI view'larını kaldır/redirect | ✅ | 3 view comment edildi (view-requirements, view-testing, view-wricef) |
| 8.7 | Dashboard stats: yeni tablolardan beslenecek şekilde güncelle | ✅ | index() route new_requirements kullanıyor |
| 8.8 | Analysis session detail: fitgap bölümü → Requirements bölümü | 📋 | UI label değişikliği gerekli |
| 8.9 | index() route: requirements → new_requirements | ✅ | SQL ve variable güncellemesi yapıldı |
| 8.10 | database.py: Legacy tablo oluşturmayı kaldır | 📋 | İleride temizlenecek |

**Test Sonuçları:**
- ✅ Legacy endpoints 404 dönüyor (decommissioned)
- ✅ New endpoints 200 dönüyor (active)
- ✅ Dashboard successfully loading

---

## PHASE 9: Defect Management 📋 BACKLOG

| ID | Task | Status |
|----|------|--------|
| 9.1 | defects tablosu | 📋 |
| 9.2 | Defects CRUD API | 📋 |
| 9.3 | Defects UI sayfası | 📋 |
| 9.4 | Severity/Priority/Category | 📋 |
| 9.5 | Status workflow (New→Open→Fixed→Retest→Closed) | 📋 |
| 9.6 | Defect → Test Case link | 📋 |
| 9.7 | "Log Defect" from Test | 📋 |

---

## PHASE 10: SAP Activate Phase Tracking ⸮ FUTURE

| ID | Task | Status |
|----|------|--------|
| 10.1 | project_phases tablosu | ⸮ |
| 10.2 | 6 phase: Discover/Prepare/Explore/Realize/Deploy/Run | ⸮ |
| 10.3 | Phase timeline visual | ⸮ |
| 10.4 | Cutover checklist | ⸮ |
| 10.5 | Go/No-Go decision | ⸮ |

---

## PHASE 11: Dashboard & Reporting ⸮ FUTURE

| ID | Task | Status |
|----|------|--------|
| 11.1 | Risk heatmap | ✅ |
| 11.2 | Test progress S-Curve | ⸮ |
| 11.3 | Traceability matrix view | ⸮ |
| 11.4 | Gap coverage report | ⸮ |
| 11.5 | PDF/Excel export | ⸮ |

---

## PHASE 12: AI Features ⸮ FUTURE

| ID | Task | Status |
|----|------|--------|
| 12.1 | OpenAI API entegrasyonu | ⸮ |
| 12.2 | Upload meeting transcript | ⸮ |
| 12.3 | Auto-extract Q&A/Actions | ⸮ |
| 12.4 | AI-powered FS/TS generation | ⸮ |
| 12.5 | Gap → WRICEF type suggestion | ⸮ |
| 12.6 | Natural language chat | ⸮ |

---

## 🎯 Sıradaki Çalışma Planı (Önerilen Sıra)

### Sprint 1: Legacy Temizlik + UI Doğrulama
**Phase 8 (8.1–8.10) + Phase 4-6-7 ⚠️ items**

Amaç: Eski ve yeni tabloların çakışmasını gidermek, UI'ın tamamen PRD-uyumlu tablolarla çalışmasını sağlamak.

1. Legacy tabloları ve API'leri devre dışı bırak
2. Dashboard/Analysis sayfalarını yeni tablolara bağla
3. Requirement, WRICEF, Config UI detaylarını tamamla
4. Convert flow'larının UI'da uçtan uca çalışmasını sağla

### Sprint 2: Composite Scenario + SIT/UAT Linkage
**Phase 3.5-3.6 + Phase 7.5-7.6**

1. Scenarios tablosuna is_composite + included_scenario_ids ekle
2. Composite scenario UI (multi-select)
3. SIT/UAT sekmelerinde scenario seçimi

### Sprint 3: Defect Management
**Phase 9**

### Sprint 4+: SAP Activate, Dashboard, AI
**Phase 10-11-12**

---

## 🗄️ PRD → DB Tablo Eşleştirme (newreq.md referans)

| PRD Entity | DB Tablosu | Durum |
|------------|-----------|-------|
| PROJECT | projects | ✅ Uyumlu |
| SCENARIO | scenarios | ⚠️ is_composite/included_scenario_ids eksik |
| ANALYSIS | analyses + analysis_sessions | ✅ İkisi birlikte çalışıyor |
| REQUIREMENT | new_requirements | ✅ PRD-uyumlu |
| WRICEF_ITEM | wricef_items | ✅ PRD-uyumlu |
| CONFIG_ITEM | config_items | ✅ PRD-uyumlu |
| TEST_CASE | test_management | ✅ PRD-uyumlu |

---

## 📁 Dosya Yapısı

```
/workspaces/ProjektCoPilot/
├── app.py                  # Flask backend (2058 satır)
├── database.py             # DB şeması (22 tablo)
├── project_copilot.db      # SQLite veritabanı
├── templates/
│   └── index.html          # Frontend (7051 satır)
├── PROGRESS_REPORT.md      # Bu dosya
├── requirements.txt
└── README.md
```

---

## 💻 Geliştirme Ortamı

| Özellik | Detay |
|---------|-------|
| Platform | GitHub Codespaces |
| Backend | Python Flask |
| Database | SQLite (WAL mode, 10s timeout) |
| Frontend | Vanilla HTML/CSS/JS + Jinja2 |
| Port | 8080 |
| Başlatma | `cd /workspaces/ProjektCoPilot && python app.py` |

---

## 👥 Contributors
- **Umut Soyyılmaz** - Product Owner, SAP Expert
- **Claude AI** - Development Partner

---

*Last Updated: 2026-02-05*
