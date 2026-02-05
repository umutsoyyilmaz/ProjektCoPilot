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
from sqlalchemy.types import TypeDecorator, Date

db = SQLAlchemy()


class SafeDate(TypeDecorator):
    impl = db.String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value in (None, ""):
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, date):
            return value.isoformat()
        return str(value)

    def process_result_value(self, value, dialect):
        if value in (None, ""):
            return None
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value).date()
            except ValueError:
                return None
        return value


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
    __tablename__ = 'projects'  # Match existing database table
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Core fields (PRD)
    code = db.Column('project_code', db.String(20), unique=True, nullable=False)
    name = db.Column('project_name', db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='Active')
    phase = db.Column('current_phase', db.String(20), nullable=True)
    start_date = db.Column(SafeDate, nullable=True)
    end_date = db.Column(SafeDate, nullable=True)
    
    # Extended fields (from existing projects table)
    customer_name = db.Column(db.String(200), nullable=True)
    customer_industry = db.Column(db.String(100), nullable=True)
    customer_country = db.Column(db.String(100), nullable=True)
    customer_contact = db.Column(db.String(200), nullable=True)
    customer_email = db.Column(db.String(200), nullable=True)
    deployment_type = db.Column(db.String(50), nullable=True)
    implementation_approach = db.Column(db.String(100), nullable=True)
    sap_modules = db.Column(db.String(500), nullable=True)
    modules = db.Column(db.String(500), nullable=True)  # Legacy field
    environment = db.Column(db.String(50), nullable=True)
    golive_planned = db.Column(SafeDate, nullable=True)
    golive_actual = db.Column(SafeDate, nullable=True)
    project_manager = db.Column(db.String(200), nullable=True)
    solution_architect = db.Column(db.String(200), nullable=True)
    functional_lead = db.Column(db.String(200), nullable=True)
    technical_lead = db.Column(db.String(200), nullable=True)
    total_budget = db.Column(db.Float, nullable=True)
    completion_percent = db.Column(db.Integer, nullable=True, default=0)
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    scenarios = db.relationship('Scenario', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    wricef_items = db.relationship('WricefItem', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    config_items = db.relationship('ConfigItem', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    test_cases = db.relationship('TestCase', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    test_cycles = db.relationship('TestCycle', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    defects = db.relationship('Defect', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'project_code': self.code,
            'project_name': self.name,
            'description': self.description,
            'status': self.status,
            'current_phase': self.phase,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'customer_name': self.customer_name,
            'customer_industry': self.customer_industry,
            'customer_country': self.customer_country,
            'customer_contact': self.customer_contact,
            'customer_email': self.customer_email,
            'deployment_type': self.deployment_type,
            'implementation_approach': self.implementation_approach,
            'sap_modules': self.sap_modules,
            'modules': self.modules,
            'environment': self.environment,
            'golive_planned': self.golive_planned.isoformat() if self.golive_planned else None,
            'golive_actual': self.golive_actual.isoformat() if self.golive_actual else None,
            'project_manager': self.project_manager,
            'solution_architect': self.solution_architect,
            'functional_lead': self.functional_lead,
            'technical_lead': self.technical_lead,
            'total_budget': self.total_budget,
            'completion_percent': self.completion_percent,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Scenario(db.Model):
    __tablename__ = 'scenarios'  # Match existing database table
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True)
    code = db.Column('scenario_id', db.String(50), nullable=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    process_area = db.Column(db.String(100), nullable=True)
    priority = db.Column(db.String(20), nullable=True, default='Medium')
    tags = db.Column(db.Text, nullable=True)
    is_composite = db.Column(db.Boolean, nullable=False, default=False)
    included_scenario_ids = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=True, default='Draft')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    analyses = db.relationship('Analysis', backref='scenario', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'scenario_id': self.code,
            'project_id': self.project_id,
            'name': self.name,
            'description': self.description,
            'process_area': self.process_area,
            'priority': self.priority,
            'status': self.status,
            'tags': self.tags,
            'is_composite': bool(self.is_composite),
            'included_scenario_ids': self.included_scenario_ids,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Analysis(db.Model):
    __tablename__ = 'analyses'  # Match existing database table (or create new)
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    scenario_id = db.Column(db.Integer, db.ForeignKey('scenarios.id', ondelete='CASCADE'), nullable=False, index=True)
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
    __tablename__ = 'new_requirements'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(db.Integer, nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='SET NULL'), nullable=True, index=True)
    gap_id = db.Column(db.Integer, nullable=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey('analyses.id', ondelete='SET NULL'), nullable=True, index=True)
    code = db.Column(db.String(20), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    module = db.Column(db.String(50), nullable=True)
    fit_type = db.Column(db.String(50), nullable=True)
    classification = db.Column(db.String(20), nullable=True)  # Fit | PartialFit | Gap
    priority = db.Column(db.String(20), nullable=True, default='Medium')
    acceptance_criteria = db.Column(db.Text, nullable=True)
    conversion_status = db.Column(db.String(20), nullable=False, default='None')
    converted_item_id = db.Column(db.Integer, nullable=True)
    converted_item_type = db.Column(db.String(20), nullable=True)
    converted_at = db.Column(db.DateTime, nullable=True)
    converted_by = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(20), nullable=True, default='Draft')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    wricef_items = db.relationship('WricefItem', backref='requirement', lazy='dynamic')
    config_items = db.relationship('ConfigItem', backref='requirement', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'project_id': self.project_id,
            'gap_id': self.gap_id,
            'analysis_id': self.analysis_id,
            'code': self.code,
            'title': self.title,
            'description': self.description,
            'module': self.module,
            'fit_type': self.fit_type,
            'classification': self.classification,
            'priority': self.priority,
            'acceptance_criteria': self.acceptance_criteria,
            'conversion_status': self.conversion_status,
            'converted_item_id': self.converted_item_id,
            'converted_item_type': self.converted_item_type,
            'converted_at': self.converted_at.isoformat() if self.converted_at else None,
            'converted_by': self.converted_by,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class WricefItem(db.Model):
    __tablename__ = 'wricef_items'  # Match existing database table
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True)
    scenario_id = db.Column(db.Integer, db.ForeignKey('scenarios.id', ondelete='SET NULL'), nullable=True)
    requirement_id = db.Column(db.Integer, db.ForeignKey('new_requirements.id', ondelete='SET NULL'), nullable=True, index=True)
    code = db.Column(db.String(20), nullable=False)
    wricef_type = db.Column(db.String(5), nullable=False)  # W/R/I/C/E/F
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    module = db.Column(db.String(20), nullable=True)
    status = db.Column(db.String(30), nullable=False, default='Draft')
    owner = db.Column(db.String(50), nullable=True)
    complexity = db.Column(db.String(20), nullable=True)
    effort_days = db.Column(db.Integer, nullable=True)
    fs_content = db.Column(db.Text, nullable=True)
    ts_content = db.Column(db.Text, nullable=True)
    unit_test_steps = db.Column(db.Text, nullable=True)
    fs_link = db.Column(db.String(500), nullable=True)
    ts_link = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    defects = db.relationship('Defect', backref='wricef', lazy='dynamic')
    __table_args__ = (db.UniqueConstraint('project_id', 'code', name='uq_wricef_project_code'),)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'scenario_id': self.scenario_id,
            'requirement_id': self.requirement_id,
            'code': self.code,
            'wricef_type': self.wricef_type,
            'title': self.title,
            'description': self.description,
            'module': self.module,
            'status': self.status,
            'owner': self.owner,
            'complexity': self.complexity,
            'effort_days': self.effort_days,
            'fs_content': self.fs_content,
            'ts_content': self.ts_content,
            'unit_test_steps': self.unit_test_steps,
            'fs_link': self.fs_link,
            'ts_link': self.ts_link,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ConfigItem(db.Model):
    __tablename__ = 'config_items'  # Match existing database table
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True)
    scenario_id = db.Column(db.Integer, db.ForeignKey('scenarios.id', ondelete='SET NULL'), nullable=True)
    requirement_id = db.Column(db.Integer, db.ForeignKey('new_requirements.id', ondelete='SET NULL'), nullable=True, index=True)
    code = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    config_type = db.Column(db.String(50), nullable=True)
    module = db.Column(db.String(20), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='Draft')
    owner = db.Column(db.String(50), nullable=True)
    config_details = db.Column(db.Text, nullable=True)
    unit_test_steps = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('project_id', 'code', name='uq_config_project_code'),)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'requirement_id': self.requirement_id,
            'code': self.code,
            'title': self.title,
            'description': self.description,
            'config_type': self.config_type,
            'module': self.module,
            'status': self.status,
            'owner': self.owner,
            'config_details': self.config_details,
            'unit_test_steps': self.unit_test_steps,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'scenario_id': self.scenario_id,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


# ===========================================================================
# TEST MANAGEMENT LAYER
# ===========================================================================

class TestCase(db.Model):
    __tablename__ = 'test_management'  # Match existing database table
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True)
    code = db.Column(db.String(20), nullable=False)
    test_type = db.Column(db.String(20), nullable=True)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='Draft')
    owner = db.Column(db.String(50), nullable=True)
    source_type = db.Column(db.String(20), nullable=True)
    source_id = db.Column(db.Integer, nullable=True)
    steps = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('project_id', 'code', name='uq_testcase_project_code'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'code': self.code,
            'test_type': self.test_type,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'owner': self.owner,
            'source_type': self.source_type,
            'source_id': self.source_id,
            'steps': self.steps,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class TestCycle(db.Model):
    __tablename__ = 'test_cycle'  # Will be created in future migration
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True)
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
    __tablename__ = 'test_execution'  # Will be created in future migration
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    test_case_id = db.Column(db.Integer, db.ForeignKey('test_management.id', ondelete='CASCADE'), nullable=False, index=True)
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
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True)
    code = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=True)
    steps_to_reproduce = db.Column(db.Text, nullable=True)
    severity = db.Column(db.String(20), nullable=True)
    priority = db.Column(db.String(20), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='New')
    test_execution_id = db.Column(db.Integer, db.ForeignKey('test_execution.id', ondelete='SET NULL'), nullable=True, index=True)
    wricef_id = db.Column(db.Integer, db.ForeignKey('wricef_items.id', ondelete='SET NULL'), nullable=True, index=True)
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
    embedding_metadata = db.Column('metadata', db.JSON, nullable=True)  # Renamed to avoid reserved word
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('entity_type', 'entity_id', 'content_hash', name='uq_embedding_entity_hash'),
    )


# ===========================================================================
# BRIDGE TABLE — Scenario ↔ TestCase (N:N for SIT/UAT)
# ===========================================================================

scenario_test_case = db.Table(
    'scenario_test_case',
    db.Column('scenario_id', db.Integer, db.ForeignKey('scenarios.id', ondelete='CASCADE'), primary_key=True),
    db.Column('test_case_id', db.Integer, db.ForeignKey('test_management.id', ondelete='CASCADE'), primary_key=True),
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
