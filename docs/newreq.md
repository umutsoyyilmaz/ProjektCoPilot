Not: Mevcut prototipte “Fit-Gap” sekmesi ve “Testing” menüsü var; bu spec o yapıyı Requirement temelli yeni modele taşıyacak şekilde kurgulanmıştır. 
index (6)

Master plan’daki mevcut entity zincirini (Project→Scenario→Workshop→Fit/Gap→Config/WRICEF→Unit Test) Requirement’a refactor ediyoruz. 
MASTER_PLAN
 
PRD / Functional Spec
Feature: Project → Scenario → Analysis → Requirement → (WRICEF/Config) → Unit Test + Test Management
1) Amaç
SAP S/4HANA dönüşüm projelerinde; iş senaryolarını, bu senaryoların analizlerini ve analizden çıkan requirement’ları tek kökten yönetmek; requirement’ların Fit/Partial Fit/Gap sınıflandırmasıyla WRICEF / Configuration backlog’una dönüşmesini sağlamak; WRICEF/Config içindeki unit test adımlarının tek tıkla Unit Test’e dönüştürülmesini ve Test Management altında farklı test türlerinde izlenmesini sağlamak.
2) Kapsam (In Scope)
•	Project hiyerarşisi altında Scenario yönetimi
•	Scenario altında Analysis yönetimi
•	Analysis altında Requirement yönetimi (Fit / Partial Fit / Gap)
•	Requirement’tan WRICEF veya Configuration item’ı üretme (convert)
•	WRICEF List ve Configuration List ekranları
•	WRICEF/Config içinde:
o	Unit Test Steps edit
o	Convert to Unit Test aksiyonu
•	Test Management ekranı:
o	Unit Test
o	SIT
o	UAT
o	String Test
o	Sprint Tests
o	Performance & Load
o	Regression
•	Scenario’ların tekil veya birleşik (composite) şekilde SIT/UAT test senaryosuna temel olması
3) Kapsam Dışı (Out of Scope - şimdilik)
•	FS/TS dokümanlarının otomatik jenerasyonu (AI) (ileride olabilir)
•	Test execution otomasyonu / entegrasyon (Jira Xray, Tricentis vb.)
•	Defect Management (sonraki faz)
•	Performans testi ölçüm altyapısı (JMeter entegrasyonu vb.)
 
4) Ürün Prensipleri (Non-negotiables)
1.	SSOT = Requirement
Fit/Partial Fit/Gap, requirement’ın “classification”’ıdır. “Fit-Gap item” ayrı bir varlık olarak yaşamaz.
2.	Scenario ≠ Test Case
Scenario iş akışıdır. Test Management’ta test case’ler scenario(lar)dan üretilir/bağlanır.
3.	Convert işlemleri izlenebilir olmalı
Requirement → WRICEF/Config ve WRICEF/Config → Unit Test dönüşümlerinde traceability zorunlu.
4.	Copy steps, keep trace
Unit Test üretirken steps snapshot olarak kopyalanır; kaynak linki korunur.
 
5) Terminoloji
•	Project: Program/implementation projesi
•	Scenario: İş senaryosu (O2C, P2P gibi), test kapsamının “bağlamı”
•	Analysis: Bir scenario altındaki analiz paketi (workshop çıktısı / breakdown)
•	Requirement: Analizin ürettiği gereksinim (Fit/Partial Fit/Gap)
•	WRICEF Item: Geliştirme/backlog nesnesi (R/I/C/E/F + W opsiyon)
•	Configuration Item: SAP standart üzerinden uyarlama maddesi
•	Unit Test: WRICEF/Config item seviyesinde geliştirici/konfigüratör testi
•	SIT/UAT Test Scenario: Scenario’lardan (tekil ya da composite) türetilen test plan/structure
 
6) Veri Modeli (Entities + İlişkiler)
6.1 Core Entities
PROJECT
•	id, code, name, status, phase, dates…
SCENARIO
•	id, project_id (FK)
•	code (SCN-001)
•	name, description
•	tags (process/module)
•	is_composite (bool)
•	included_scenario_ids (array / relation table) (sadece composite ise)
•	created_at, updated_at
ANALYSIS
•	id, scenario_id (FK)
•	code (ANL-001)
•	title, description
•	owner, status
•	created_at, updated_at
REQUIREMENT
•	id, analysis_id (FK)
•	code (REQ-001)
•	title, description
•	classification: Fit | PartialFit | Gap
•	priority: Must/Should/Could (opsiyon)
•	acceptance_criteria (opsiyon)
•	conversion_status: None | WRICEF | CONFIG
•	converted_item_id (nullable)
•	converted_at, converted_by
WRICEF_ITEM
•	id, project_id (FK), scenario_id (FK opsiyon), requirement_id (FK)
•	code (WR-001)
•	wricef_type: W/R/I/C/E/F
•	title, description
•	status, owner
•	fs_content / fs_link
•	ts_content / ts_link
•	unit_test_steps (json array)
•	created_at, updated_at
CONFIG_ITEM
•	id, project_id (FK), scenario_id (FK opsiyon), requirement_id (FK)
•	code (CFG-001)
•	title, description
•	status, owner
•	config_details (rich text / json) (SSCUI, path, param, dependency)
•	unit_test_steps (json array)
•	created_at, updated_at
TEST_CASE
•	id, project_id (FK)
•	code (TST-001)
•	test_type: Unit | SIT | UAT | String | Sprint | PerformanceLoad | Regression
•	title, description
•	status: Draft/Ready/Executed/Passed/Failed/Blocked (minimum)
•	owner
•	source_type: WRICEF | CONFIG | SCENARIO | COMPOSITE_SCENARIO
•	source_id
•	steps (json array) (Unit test conversion’da dolu gelir)
•	created_at, updated_at
6.2 Relationship Highlights
•	Project 1—N Scenario
•	Scenario 1—N Analysis
•	Analysis 1—N Requirement
•	Requirement 0..1—1 WRICEF_ITEM veya 0..1—1 CONFIG_ITEM
•	WRICEF/Config 0..N—N TEST_CASE (özellikle Unit + Regression reuse için)
•	Scenario N—N Test Case (SIT/UAT senaryoları scenario referanslı)
 
7) Kullanıcı Rolleri (Minimum)
•	Project Manager / PO: hepsini görür, create/convert yetkisi
•	Business Analyst: scenario/analysis/requirement yönetir, convert edebilir
•	Consultant/Developer: wricef/config üzerinde FS/TS + unit steps girer, unit test’e çevirir
•	Tester/Key User: test management’ta execution/update (ileride)
 
8) UI/UX Bilgi Mimarisi (Ekranlar)
8.1 Project Object Page (Top Level)
Sekmeler:
1.	Scenarios
2.	Analyses (opsiyonel global görünüm)
3.	Requirements (opsiyonel global explorer)
4.	WRICEF List
5.	Configuration List
6.	Test Management
8.2 Scenarios Screen
•	Scenario cards/grid veya list
•	Scenario detail:
o	Included scenarios (composite ise)
o	Analyses listesi (child)
Scenario Composite davranış
•	“Create Composite Scenario” ile:
o	scenario seçimi (multi-select)
o	“This is a SIT/UAT composite candidate” notu (opsiyon)
8.3 Analysis Screen (Scenario altında)
•	Analysis listesi
•	Analysis detail içinde:
o	Requirements tablosu (ana iş)
8.4 Requirements Table (Analysis detail içinde)
Kolonlar:
•	Req Code
•	Title
•	Classification badge (Fit/Partial Fit/Gap)
•	Priority (opsiyon)
•	Conversion Status (None/WRICEF/CONFIG)
•	Actions
Actions (şartlı)
•	Fit → Convert to Configuration Item (aktif)
•	Partial Fit / Gap → Convert to WRICEF Item (aktif)
Convert sonrası UI
•	Conversion Status badge + “Open created item” link
•	Aynı requirement tekrar convert edilemez (edit/rollback ayrı konu)
8.5 WRICEF List Screen
•	Liste/filtre (type, status, module, scenario, requirement)
•	Item detail içinde alanlar:
o	FS
o	TS
o	Unit Test Steps editor
o	Convert to Unit Test butonu
8.6 Configuration List Screen
•	Liste/filtre (module, status, scenario, requirement)
•	Item detail içinde alanlar:
o	Config Details
o	Unit Test Steps editor
o	Convert to Unit Test butonu
8.7 Test Management Screen
Sekmeler:
•	Unit Tests
•	SIT
•	UAT
•	String Tests
•	Sprint Tests
•	Performance & Load Tests
•	Regression Tests
Her sekmede:
•	Test case listesi + filtreler (status, owner, scenario, source)
•	Test detail (steps, evidence, execution status)
 
9) İş Kuralları (Business Rules)
9.1 Requirement Classification
•	classification zorunlu: Fit / Partial Fit / Gap
•	listede badge olarak görünür (filterable)
9.2 Requirement → Convert
•	Eğer classification = Fit:
o	convert target = CONFIG_ITEM
•	Eğer classification = Gap veya Partial Fit:
o	convert target = WRICEF_ITEM
•	Convert sonrası requirement alanları set edilir:
o	conversion_status
o	converted_item_id
o	converted_at/by
9.3 Converted Lists
•	WRICEF List yalnız WRICEF_ITEM’ları gösterir
•	Configuration List yalnız CONFIG_ITEM’ları gösterir
•	Her item, kaynak requirement’ı linkler
9.4 WRICEF/CONFIG → Convert to Unit Test
•	Button adı: Convert to Unit Test
•	Pre-condition: unit_test_steps boş olamaz
•	Action:
o	Yeni TEST_CASE oluştur:
	test_type = Unit
	source_type = WRICEF/CONFIG
	source_id = item.id
	steps = item.unit_test_steps (snapshot)
•	Post-condition:
o	Unit Tests listesinde görünür
o	source item’da “Created Unit Test: UT-xxx” linki çıkar (opsiyon: multi)
9.5 SIT/UAT Test Scenarios (Single vs Composite)
Test Management tarafında SIT ve UAT sekmeleri “test plan” mantığında çalışır:
•	Single: 1 Scenario referansı ile SIT/UAT test case seti
•	Composite: N Scenario referansı ile SIT/UAT test case seti
Minimum model:
•	SIT/UAT test case kaydı:
o	source_type = SCENARIO veya COMPOSITE_SCENARIO
o	source_id = scenario_id (tekil) veya composite_scenario_id
Composite scenario’yu ayrı bir scenario olarak tutuyorsan SCENARIO.is_composite=true zaten yeterli.
 
10) Kabul Kriterleri (Acceptance Criteria)
AC-01: Hiyerarşi
•	Project altında senaryolar listelenir.
•	Her scenario altında analizler listelenir.
•	Her analiz altında requirement’lar listelenir.
AC-02: Requirement listesi ve sınıflandırma
•	Requirement listesinde Fit/Partial Fit/Gap görünür ve filtrelenebilir.
AC-03: Convert butonları doğru çalışır
•	Fit requirement’ta sadece “Convert to Configuration Item” aktif.
•	Gap/Partial Fit requirement’ta sadece “Convert to WRICEF Item” aktif.
AC-04: Convert edilenler doğru listelerde görünür
•	WRICEF’e convert edilen requirement, WRICEF List’te görünür.
•	Config’e convert edilen requirement, Configuration List’te görünür.
AC-05: WRICEF item içeriği
•	WRICEF item detail içinde FS, TS, Unit Test Steps alanları vardır.
AC-06: Config item içeriği
•	Config item detail içinde Config Details, Unit Test Steps alanları vardır.
AC-07: Convert to Unit Test snapshot + trace
•	WRICEF/Config item’dan Unit Test oluşturulduğunda:
o	Unit test steps aynen test case’e taşınır (snapshot)
o	test case kaynağı (WRICEF/CONFIG) linklenir (traceability)
AC-08: Test Management sekmeleri
•	Unit/SIT/UAT/String/Sprint/Performance&Load/Regression ayrı sekme olarak görünür.
 
11) Edge Cases / Karar Noktaları (PM notları)
1.	Requirement classification convert sonrası değişirse ne olacak?
o	Öneri: Convert sonrası classification değişirse:
	ya “locked” (basit)
	ya da “re-convert” flow (ileri seviye)
2.	Bir requirement birden fazla WRICEF/Config yaratabilir mi?
o	Şimdilik hayır (1:1) → kontrol ve izlenebilirlik için en sağlıklısı
3.	Bir WRICEF/Config birden fazla unit test üretebilir mi?
o	Olabilir (farklı varyantlar) ama MVP’de:
	“Created Tests” listesi tutarak N adet desteklenebilir
 
12) Mevcut Prototip ile Map (Refactor Plan)
Mevcut prototipte “Fit-Gap” tab’ı var; bunu:
•	Label: Requirements
•	filter: Fit / Partial Fit / Gap
•	“Add Item” modal’ı “Add Requirement” olur
•	Convert butonları eklenir

index (6)
Master plan’daki zincirde Fit/GAP objesi vardı; artık:
•	Fit/GAP yerine Requirement entity temel alınacak

MASTER_PLAN
 
13) Dev’e verilecek net task breakdown (Epic/Story formatı)
EPIC-A: Requirement Refactor
•	A1: Fit-Gap UI → Requirement UI (labels + fields)
•	A2: Requirement classification (Fit/Partial/Gap) + filters
•	A3: Requirement conversion fields (conversion_status, converted_id)
EPIC-B: Convert Flows
•	B1: Convert Fit → Config item create
•	B2: Convert Gap/Partial → Wricef item create
•	B3: Requirement satırında “open created item” link
EPIC-C: WRICEF & Config Detail Enhancements
•	C1: WRICEF detail: FS/TS + unit steps editor
•	C2: Config detail: config details + unit steps editor
•	C3: Convert to Unit Test button + validations
EPIC-D: Test Management Expansion
•	D1: Test type taxonomy (Unit/SIT/UAT/String/Sprint/Perf/Regression)
•	D2: UI: 7 tab structure
•	D3: Unit test list + detail + source trace
•	D4: SIT/UAT model: single vs composite scenario linkage

