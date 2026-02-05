"""
Integration tests for ProjektCoPilot API endpoints
"""
import pytest
import os
import tempfile
import uuid
from app import app, get_db_connection


def unique_code(prefix="TEST"):
    """Generate unique project code for tests"""
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


@pytest.fixture
def client():
    """Test client fixture"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def temp_db():
    """Create a temporary test database"""
    db_fd, db_path = tempfile.mkstemp()
    # Note: In production, you'd want to initialize schema here
    yield db_path
    os.close(db_fd)
    os.unlink(db_path)


class TestIndexEndpoint:
    """Test the main index page"""
    
    def test_index_loads(self, client):
        """Index page should return 200"""
        response = client.get('/')
        assert response.status_code == 200


class TestProjectsAPI:
    """Test /api/projects endpoints"""
    
    def test_get_projects(self, client):
        """GET /api/projects should return projects list"""
        response = client.get('/api/projects')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
    
    def test_add_project_success(self, client):
        """POST /api/projects with valid data should succeed"""
        payload = {
            'project_code': 'TEST-001',
            'project_name': 'Test Project',
            'description': 'Test description',
            'status': 'Planning'
        }
        response = client.post('/api/projects', json=payload)
        assert response.status_code == 201
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'id' in data
    
    def test_add_project_missing_fields(self, client):
        """POST /api/projects without required fields should fail"""
        payload = {'description': 'Missing required fields'}
        response = client.post('/api/projects', json=payload)
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert data['error'] == 'missing_fields'
    
    def test_get_project_by_id(self, client):
        """GET /api/projects/<id> should return project details"""
        # First create a project
        payload = {
            'project_code': 'TEST-002',
            'project_name': 'Test Project 2'
        }
        create_response = client.post('/api/projects', json=payload)
        project_id = create_response.get_json()['id']
        
        # Then fetch it
        response = client.get(f'/api/projects/{project_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['project_code'] == 'TEST-002'


class TestRequirementsAPI:
    """Test /api/requirements endpoints"""
    
    def test_get_requirements(self, client):
        """GET /api/requirements should return requirements list"""
        response = client.get('/api/requirements')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
    
    def test_add_requirement_success(self, client):
        """POST /api/requirements with valid data should succeed"""
        payload = {
            'code': 'REQ-TEST-001',
            'title': 'Test Requirement',
            'module': 'MM',
            'complexity': 'Low'
        }
        response = client.post('/api/requirements', json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
    
    def test_add_requirement_missing_fields(self, client):
        """POST /api/requirements without required fields should fail"""
        payload = {'module': 'MM'}  # missing code and title
        response = client.post('/api/requirements', json=payload)
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data


class TestSessionsAPI:
    """Test /api/sessions endpoints"""
    
    def test_get_sessions(self, client):
        """GET /api/sessions should return sessions list"""
        response = client.get('/api/sessions')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
    
    def test_add_session_success(self, client):
        """POST /api/sessions with valid data should succeed"""
        # First create a project
        project_payload = {
            'project_code': 'TEST-SESS-001',
            'project_name': 'Session Test Project'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        # Then create a session
        session_payload = {
            'project_id': project_id,
            'session_name': 'Test Workshop',
            'module': 'MM',
            'status': 'Planned'
        }
        response = client.post('/api/sessions', json=session_payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
    
    def test_add_session_missing_fields(self, client):
        """POST /api/sessions without required fields should fail"""
        payload = {'module': 'MM'}  # missing project_id and session_name
        response = client.post('/api/sessions', json=payload)
        assert response.status_code == 400


class TestQuestionsAPI:
    """Test /api/questions endpoints"""
    
    def test_get_questions(self, client):
        """GET /api/questions should return questions list"""
        response = client.get('/api/questions')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
    
    def test_add_question_success(self, client):
        """POST /api/questions with valid data should succeed"""
        # First create project and session
        project_payload = {
            'project_code': 'TEST-Q-001',
            'project_name': 'Question Test Project'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        session_payload = {
            'project_id': project_id,
            'session_name': 'Q Test Workshop'
        }
        session_response = client.post('/api/sessions', json=session_payload)
        # Get session_id from database since POST doesn't return it
        from app import db_conn
        with db_conn() as conn:
            session = conn.execute(
                'SELECT id FROM analysis_sessions WHERE project_id = ? ORDER BY id DESC LIMIT 1',
                (project_id,)
            ).fetchone()
            session_id = session['id'] if session else None
        
        # Then create a question
        question_payload = {
            'session_id': session_id,
            'question_text': 'What is the procurement process?',
            'status': 'Open'
        }
        response = client.post('/api/questions', json=question_payload)
        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert 'id' in data
    
    def test_add_question_missing_fields(self, client):
        """POST /api/questions without required fields should fail"""
        payload = {'status': 'Open'}  # missing session_id and question_text
        response = client.post('/api/questions', json=payload)
        assert response.status_code == 400


class TestStatsAPI:
    """Test /api/analysis/stats endpoint"""
    
    def test_get_stats_without_project(self, client):
        """GET /api/analysis/stats should return general stats"""
        response = client.get('/api/analysis/stats')
        assert response.status_code == 200
        data = response.get_json()
        assert 'total_sessions' in data
        assert 'gap_count' in data
        assert 'open_questions' in data
    
    def test_get_stats_with_project(self, client):
        """GET /api/analysis/stats?project_id=X should return project-specific stats"""
        # Create a project first
        project_payload = {
            'project_code': 'TEST-STATS-001',
            'project_name': 'Stats Test Project'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        response = client.get(f'/api/analysis/stats?project_id={project_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert 'total_sessions' in data
        # Project stats may or may not include project object depending on implementation


class TestChatAPI:
    """Test /api/chat endpoint"""
    
    def test_chat_endpoint(self, client):
        """POST /api/chat should return a reply"""
        payload = {'message': 'Hello'}
        response = client.post('/api/chat', json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert 'reply' in data


class TestScenariosAPI:
    """Test /api/scenarios endpoints (Epic A1)"""
    
    def test_get_scenarios(self, client):
        """GET /api/scenarios should return scenarios list"""
        response = client.get('/api/scenarios')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
    
    def test_get_scenarios_by_project(self, client):
        """GET /api/scenarios?project_id=X should filter by project"""
        # Create a project
        project_payload = {
            'project_code': 'TEST-SCN-001',
            'project_name': 'Scenario Test Project'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        # Create a scenario
        scenario_payload = {
            'project_id': project_id,
            'name': 'Purchase Order Creation',
            'description': 'Create new PO in SAP',
            'process_area': 'MM'
        }
        client.post('/api/scenarios', json=scenario_payload)
        
        # Get scenarios for this project
        response = client.get(f'/api/scenarios?project_id={project_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) >= 1
    
    def test_add_simple_scenario_success(self, client):
        """POST /api/scenarios with valid data should create simple scenario"""
        # Create a project
        project_payload = {
            'project_code': 'TEST-SCN-002',
            'project_name': 'Scenario Test 2'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        # Create a simple scenario
        scenario_payload = {
            'project_id': project_id,
            'name': 'Goods Receipt',
            'description': 'Receive goods in warehouse',
            'process_area': 'MM',
            'status': 'Draft'
        }
        response = client.post('/api/scenarios', json=scenario_payload)
        assert response.status_code == 201
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'id' in data
        assert 'scenario_id' in data
    
    def test_add_composite_scenario_success(self, client):
        """POST /api/scenarios with composite flag should create composite scenario"""
        # Create a project
        project_payload = {
            'project_code': 'TEST-SCN-003',
            'project_name': 'Composite Scenario Test'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        # Create two simple scenarios
        scenario1_payload = {
            'project_id': project_id,
            'name': 'Create PO',
            'description': 'Create purchase order'
        }
        response1 = client.post('/api/scenarios', json=scenario1_payload)
        scenario1_id = response1.get_json()['id']
        
        scenario2_payload = {
            'project_id': project_id,
            'name': 'Receive Goods',
            'description': 'Goods receipt'
        }
        response2 = client.post('/api/scenarios', json=scenario2_payload)
        scenario2_id = response2.get_json()['id']
        
        # Create composite scenario
        composite_payload = {
            'project_id': project_id,
            'name': 'Complete Procurement Flow',
            'description': 'End-to-end procurement process',
            'is_composite': 1,
            'included_scenario_ids': [scenario1_id, scenario2_id],
            'tags': ['procurement', 'e2e']
        }
        response = client.post('/api/scenarios', json=composite_payload)
        assert response.status_code == 201
        data = response.get_json()
        assert data['status'] == 'success'
    
    def test_add_composite_scenario_without_includes_fails(self, client):
        """POST composite scenario without included_scenario_ids should fail"""
        # Create a project
        project_payload = {
            'project_code': 'TEST-SCN-004',
            'project_name': 'Composite Fail Test'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        # Try to create composite scenario without includes
        composite_payload = {
            'project_id': project_id,
            'name': 'Invalid Composite',
            'is_composite': 1,
            'included_scenario_ids': []  # Empty!
        }
        response = client.post('/api/scenarios', json=composite_payload)
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
    
    def test_add_scenario_missing_fields(self, client):
        """POST /api/scenarios without required fields should fail"""
        payload = {'description': 'Missing required fields'}
        response = client.post('/api/scenarios', json=payload)
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
    
    def test_get_scenario_by_id(self, client):
        """GET /api/scenarios/<id> should return scenario details"""
        # Create a project and scenario
        project_payload = {
            'project_code': 'TEST-SCN-005',
            'project_name': 'Get Scenario Test'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        scenario_payload = {
            'project_id': project_id,
            'name': 'Invoice Posting',
            'tags': ['finance', 'AP']
        }
        create_response = client.post('/api/scenarios', json=scenario_payload)
        scenario_id = create_response.get_json()['id']
        
        # Fetch scenario
        response = client.get(f'/api/scenarios/{scenario_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['name'] == 'Invoice Posting'
        assert 'analyses_count' in data
        # Tags should be parsed into array
        if data.get('tags'):
            assert isinstance(data['tags'], list)
    
    def test_get_scenario_expanded_composite(self, client):
        """GET /api/scenarios/<id> for composite should include expanded scenarios"""
        # Create project and simple scenarios
        project_payload = {
            'project_code': 'TEST-SCN-006',
            'project_name': 'Expanded Composite Test'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        s1_response = client.post('/api/scenarios', json={
            'project_id': project_id,
            'name': 'Step 1'
        })
        s1_id = s1_response.get_json()['id']
        
        s2_response = client.post('/api/scenarios', json={
            'project_id': project_id,
            'name': 'Step 2'
        })
        s2_id = s2_response.get_json()['id']
        
        # Create composite
        composite_response = client.post('/api/scenarios', json={
            'project_id': project_id,
            'name': 'Full Flow',
            'is_composite': 1,
            'included_scenario_ids': [s1_id, s2_id]
        })
        composite_id = composite_response.get_json()['id']
        
        # Fetch composite scenario
        response = client.get(f'/api/scenarios/{composite_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['is_composite'] == 1
        assert 'included_scenarios' in data
        assert len(data['included_scenarios']) == 2
    
    def test_update_scenario(self, client):
        """PUT /api/scenarios/<id> should update scenario"""
        # Create project and scenario
        project_payload = {
            'project_code': 'TEST-SCN-007',
            'project_name': 'Update Test'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        scenario_payload = {
            'project_id': project_id,
            'name': 'Original Name'
        }
        create_response = client.post('/api/scenarios', json=scenario_payload)
        scenario_id = create_response.get_json()['id']
        
        # Update scenario
        update_payload = {
            'name': 'Updated Name',
            'status': 'Active',
            'tags': ['updated']
        }
        response = client.put(f'/api/scenarios/{scenario_id}', json=update_payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        
        # Verify update
        get_response = client.get(f'/api/scenarios/{scenario_id}')
        updated_data = get_response.get_json()
        assert updated_data['name'] == 'Updated Name'
    
    def test_update_scenario_to_composite(self, client):
        """PUT /api/scenarios/<id> can convert simple to composite scenario"""
        # Create project and scenarios
        project_payload = {
            'project_code': 'TEST-SCN-008',
            'project_name': 'Convert to Composite Test'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        # Create simple scenario that will be converted
        main_response = client.post('/api/scenarios', json={
            'project_id': project_id,
            'name': 'Main Scenario'
        })
        main_id = main_response.get_json()['id']
        
        # Create included scenarios
        s1_response = client.post('/api/scenarios', json={
            'project_id': project_id,
            'name': 'Sub Scenario 1'
        })
        s1_id = s1_response.get_json()['id']
        
        # Update main to composite
        response = client.put(f'/api/scenarios/{main_id}', json={
            'is_composite': 1,
            'included_scenario_ids': [s1_id]
        })
        assert response.status_code == 200
    
    def test_update_scenario_cannot_include_self(self, client):
        """PUT /api/scenarios/<id> should reject self-inclusion"""
        # Create project and scenario
        project_payload = {
            'project_code': 'TEST-SCN-009',
            'project_name': 'Self Include Test'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        scenario_response = client.post('/api/scenarios', json={
            'project_id': project_id,
            'name': 'Test Scenario'
        })
        scenario_id = scenario_response.get_json()['id']
        
        # Try to include self
        response = client.put(f'/api/scenarios/{scenario_id}', json={
            'is_composite': 1,
            'included_scenario_ids': [scenario_id]
        })
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
    
    def test_delete_scenario_success(self, client):
        """DELETE /api/scenarios/<id> should delete scenario"""
        # Create project and scenario
        project_payload = {
            'project_code': 'TEST-SCN-010',
            'project_name': 'Delete Test'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        scenario_payload = {
            'project_id': project_id,
            'name': 'To Be Deleted'
        }
        create_response = client.post('/api/scenarios', json=scenario_payload)
        scenario_id = create_response.get_json()['id']
        
        # Delete scenario
        response = client.delete(f'/api/scenarios/{scenario_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        
        # Verify deletion
        get_response = client.get(f'/api/scenarios/{scenario_id}')
        assert get_response.status_code == 404
    
    def test_delete_scenario_in_composite_fails(self, client):
        """DELETE scenario that is included in composite should fail"""
        # Create project
        project_payload = {
            'project_code': 'TEST-SCN-011',
            'project_name': 'Delete Composite Check Test'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        # Create simple scenario
        simple_response = client.post('/api/scenarios', json={
            'project_id': project_id,
            'name': 'Simple Scenario'
        })
        simple_id = simple_response.get_json()['id']
        
        # Create composite that includes it
        client.post('/api/scenarios', json={
            'project_id': project_id,
            'name': 'Composite Scenario',
            'is_composite': 1,
            'included_scenario_ids': [simple_id]
        })
        
        # Try to delete simple scenario
        response = client.delete(f'/api/scenarios/{simple_id}')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'composite' in data['error'].lower()


class TestAnalysesAPI:
    """Test /api/analyses endpoints (Epic A2)"""
    
    def test_get_analyses(self, client):
        """GET /api/analyses should return analyses list"""
        response = client.get('/api/analyses')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
    
    def test_get_analyses_by_scenario(self, client):
        """GET /api/analyses?scenario_id=X should filter by scenario"""
        # Create project and scenario
        project_payload = {
            'project_code': unique_code('ANL'),
            'project_name': 'Analysis Test Project'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        scenario_payload = {
            'project_id': project_id,
            'name': 'Test Scenario for Analysis'
        }
        scenario_response = client.post('/api/scenarios', json=scenario_payload)
        scenario_id = scenario_response.get_json()['id']
        
        # Create an analysis
        analysis_payload = {
            'scenario_id': scenario_id,
            'title': 'Gap Analysis',
            'description': 'Analyze gaps in procurement process'
        }
        client.post('/api/analyses', json=analysis_payload)
        
        # Get analyses for this scenario
        response = client.get(f'/api/analyses?scenario_id={scenario_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) >= 1
        assert data[0]['scenario_id'] == scenario_id
    
    def test_add_analysis_success(self, client):
        """POST /api/analyses with valid data should create analysis"""
        # Create project and scenario
        project_payload = {
            'project_code': unique_code('ANL'),
            'project_name': 'Analysis Test 2'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        scenario_payload = {
            'project_id': project_id,
            'name': 'PO Process'
        }
        scenario_response = client.post('/api/scenarios', json=scenario_payload)
        scenario_id = scenario_response.get_json()['id']
        
        # Create analysis
        analysis_payload = {
            'scenario_id': scenario_id,
            'title': 'Business Process Analysis',
            'description': 'Detailed analysis of PO creation process',
            'owner': 'John Doe',
            'status': 'In Progress'
        }
        response = client.post('/api/analyses', json=analysis_payload)
        assert response.status_code == 201
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'id' in data
        assert 'code' in data
        # Code should have ANL prefix
        if data['code']:
            assert 'ANL' in data['code']
    
    def test_add_analysis_missing_fields(self, client):
        """POST /api/analyses without required fields should fail"""
        payload = {'description': 'Missing required fields'}
        response = client.post('/api/analyses', json=payload)
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
    
    def test_add_analysis_invalid_scenario(self, client):
        """POST /api/analyses with invalid scenario_id should fail"""
        payload = {
            'scenario_id': 999999,
            'title': 'Invalid Analysis'
        }
        response = client.post('/api/analyses', json=payload)
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
    
    def test_get_analysis_by_id(self, client):
        """GET /api/analyses/<id> should return analysis details"""
        # Create project, scenario, and analysis
        project_payload = {
            'project_code': unique_code('ANL'),
            'project_name': 'Get Analysis Test'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        scenario_payload = {
            'project_id': project_id,
            'name': 'Test Scenario'
        }
        scenario_response = client.post('/api/scenarios', json=scenario_payload)
        scenario_id = scenario_response.get_json()['id']
        
        analysis_payload = {
            'scenario_id': scenario_id,
            'title': 'Detailed Analysis'
        }
        create_response = client.post('/api/analyses', json=analysis_payload)
        analysis_id = create_response.get_json()['id']
        
        # Fetch analysis
        response = client.get(f'/api/analyses/{analysis_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['title'] == 'Detailed Analysis'
        assert 'scenario' in data
        assert 'requirements_count' in data
    
    def test_get_analysis_not_found(self, client):
        """GET /api/analyses/<id> with invalid id should return 404"""
        response = client.get('/api/analyses/999999')
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
    
    def test_update_analysis(self, client):
        """PUT /api/analyses/<id> should update analysis"""
        # Create project, scenario, and analysis
        project_payload = {
            'project_code': unique_code('ANL'),
            'project_name': 'Update Analysis Test'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        scenario_payload = {
            'project_id': project_id,
            'name': 'Test Scenario'
        }
        scenario_response = client.post('/api/scenarios', json=scenario_payload)
        scenario_id = scenario_response.get_json()['id']
        
        analysis_payload = {
            'scenario_id': scenario_id,
            'title': 'Original Title'
        }
        create_response = client.post('/api/analyses', json=analysis_payload)
        analysis_id = create_response.get_json()['id']
        
        # Update analysis
        update_payload = {
            'title': 'Updated Title',
            'status': 'Completed',
            'owner': 'Jane Smith'
        }
        response = client.put(f'/api/analyses/{analysis_id}', json=update_payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        
        # Verify update
        get_response = client.get(f'/api/analyses/{analysis_id}')
        updated_data = get_response.get_json()
        assert updated_data['title'] == 'Updated Title'
        assert updated_data['status'] == 'Completed'
    
    def test_update_analysis_not_found(self, client):
        """PUT /api/analyses/<id> with invalid id should return 404"""
        response = client.put('/api/analyses/999999', json={'title': 'Test'})
        assert response.status_code == 404
    
    def test_delete_analysis_success(self, client):
        """DELETE /api/analyses/<id> should delete analysis"""
        # Create project, scenario, and analysis
        project_payload = {
            'project_code': unique_code('ANL'),
            'project_name': 'Delete Analysis Test'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        scenario_payload = {
            'project_id': project_id,
            'name': 'Test Scenario'
        }
        scenario_response = client.post('/api/scenarios', json=scenario_payload)
        scenario_id = scenario_response.get_json()['id']
        
        analysis_payload = {
            'scenario_id': scenario_id,
            'title': 'To Be Deleted'
        }
        create_response = client.post('/api/analyses', json=analysis_payload)
        analysis_id = create_response.get_json()['id']
        
        # Delete analysis
        response = client.delete(f'/api/analyses/{analysis_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        
        # Verify deletion
        get_response = client.get(f'/api/analyses/{analysis_id}')
        assert get_response.status_code == 404
    
    def test_delete_analysis_not_found(self, client):
        """DELETE /api/analyses/<id> with invalid id should return 404"""
        response = client.delete('/api/analyses/999999')
        assert response.status_code == 404
    
    def test_delete_analysis_with_requirements_fails(self, client):
        """DELETE analysis with related requirements should fail"""
        # Setup complete hierarchy
        project_payload = {
            'project_code': unique_code('ANL'),
            'project_name': 'Delete Check Test'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        scenario_response = client.post('/api/scenarios', json={
            'project_id': project_id,
            'name': 'Test Scenario'
        })
        scenario_id = scenario_response.get_json()['id']
        
        analysis_response = client.post('/api/analyses', json={
            'scenario_id': scenario_id,
            'title': 'Analysis with Requirements'
        })
        analysis_id = analysis_response.get_json()['id']
        
        # Create a requirement linked to this analysis
        client.post('/api/new_requirements', json={
            'analysis_id': analysis_id,
            'title': 'Linked Requirement'
        })
        
        # Try to delete analysis - should fail
        response = client.delete(f'/api/analyses/{analysis_id}')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'requirement' in data['error'].lower()


class TestNewRequirementsAPI:
    """Test /api/new_requirements endpoints (Epic A3)"""
    
    def test_get_requirements(self, client):
        """GET /api/new_requirements should return requirements list"""
        response = client.get('/api/new_requirements')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
    
    def test_get_requirements_by_analysis(self, client):
        """GET /api/new_requirements?analysis_id=X should filter by analysis"""
        # Create project, scenario, and analysis
        project_payload = {
            'project_code': unique_code('REQ'),
            'project_name': 'Requirements Test Project'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        scenario_payload = {
            'project_id': project_id,
            'name': 'PO Scenario'
        }
        scenario_response = client.post('/api/scenarios', json=scenario_payload)
        scenario_id = scenario_response.get_json()['id']
        
        analysis_payload = {
            'scenario_id': scenario_id,
            'title': 'Gap Analysis'
        }
        analysis_response = client.post('/api/analyses', json=analysis_payload)
        analysis_id = analysis_response.get_json()['id']
        
        # Create a requirement
        req_payload = {
            'analysis_id': analysis_id,
            'title': 'Custom approval workflow needed',
            'classification': 'Gap',
            'description': 'Standard SAP approval does not meet requirements'
        }
        client.post('/api/new_requirements', json=req_payload)
        
        # Get requirements for this analysis
        response = client.get(f'/api/new_requirements?analysis_id={analysis_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) >= 1
        assert data[0]['analysis_id'] == analysis_id
    
    def test_get_requirements_by_classification(self, client):
        """GET /api/new_requirements?classification=Gap should filter by classification"""
        # Create complete hierarchy
        project_payload = {
            'project_code': unique_code('REQ'),
            'project_name': 'Classification Test'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        scenario_response = client.post('/api/scenarios', json={
            'project_id': project_id,
            'name': 'Test Scenario'
        })
        scenario_id = scenario_response.get_json()['id']
        
        analysis_response = client.post('/api/analyses', json={
            'scenario_id': scenario_id,
            'title': 'Analysis'
        })
        analysis_id = analysis_response.get_json()['id']
        
        # Create requirements with different classifications
        client.post('/api/new_requirements', json={
            'analysis_id': analysis_id,
            'title': 'Gap Requirement',
            'classification': 'Gap'
        })
        
        client.post('/api/new_requirements', json={
            'analysis_id': analysis_id,
            'title': 'Fit Requirement',
            'classification': 'Fit'
        })
        
        # Filter by classification
        response = client.get('/api/new_requirements?classification=Gap')
        assert response.status_code == 200
        data = response.get_json()
        # Should have at least our Gap requirement
        gap_reqs = [r for r in data if r['classification'] == 'Gap']
        assert len(gap_reqs) >= 1
    
    def test_add_requirement_success(self, client):
        """POST /api/new_requirements with valid data should create requirement"""
        # Setup hierarchy
        project_payload = {
            'project_code': unique_code('REQ'),
            'project_name': 'New Req Test'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        scenario_response = client.post('/api/scenarios', json={
            'project_id': project_id,
            'name': 'Finance Scenario'
        })
        scenario_id = scenario_response.get_json()['id']
        
        analysis_response = client.post('/api/analyses', json={
            'scenario_id': scenario_id,
            'title': 'Finance Gap Analysis'
        })
        analysis_id = analysis_response.get_json()['id']
        
        # Create requirement
        req_payload = {
            'analysis_id': analysis_id,
            'title': 'Multi-level approval required',
            'description': 'System needs 3-level approval workflow',
            'classification': 'PartialFit',
            'priority': 'High',
            'acceptance_criteria': 'Users can configure approval levels'
        }
        response = client.post('/api/new_requirements', json=req_payload)
        assert response.status_code == 201
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'id' in data
        assert 'code' in data
        # Code should have REQ prefix
        if data['code']:
            assert 'REQ' in data['code']
    
    def test_add_requirement_missing_fields(self, client):
        """POST /api/new_requirements without required fields should fail"""
        payload = {'description': 'Missing title and analysis_id'}
        response = client.post('/api/new_requirements', json=payload)
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
    
    def test_add_requirement_invalid_classification(self, client):
        """POST /api/new_requirements with invalid classification should fail"""
        # Setup hierarchy
        project_payload = {
            'project_code': unique_code('REQ'),
            'project_name': 'Invalid Class Test'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        scenario_response = client.post('/api/scenarios', json={
            'project_id': project_id,
            'name': 'Test'
        })
        scenario_id = scenario_response.get_json()['id']
        
        analysis_response = client.post('/api/analyses', json={
            'scenario_id': scenario_id,
            'title': 'Test'
        })
        analysis_id = analysis_response.get_json()['id']
        
        # Try invalid classification
        payload = {
            'analysis_id': analysis_id,
            'title': 'Test Requirement',
            'classification': 'InvalidType'
        }
        response = client.post('/api/new_requirements', json=payload)
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'classification' in data['error'].lower()
    
    def test_add_requirement_invalid_analysis(self, client):
        """POST /api/new_requirements with invalid analysis_id should fail"""
        payload = {
            'analysis_id': 999999,
            'title': 'Test Requirement'
        }
        response = client.post('/api/new_requirements', json=payload)
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
    
    def test_get_requirement_by_id(self, client):
        """GET /api/new_requirements/<id> should return requirement details"""
        # Setup and create requirement
        project_payload = {
            'project_code': unique_code('REQ'),
            'project_name': 'Get Req Test'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        scenario_response = client.post('/api/scenarios', json={
            'project_id': project_id,
            'name': 'Test'
        })
        scenario_id = scenario_response.get_json()['id']
        
        analysis_response = client.post('/api/analyses', json={
            'scenario_id': scenario_id,
            'title': 'Test Analysis'
        })
        analysis_id = analysis_response.get_json()['id']
        
        create_response = client.post('/api/new_requirements', json={
            'analysis_id': analysis_id,
            'title': 'Detailed Requirement',
            'classification': 'Gap'
        })
        req_id = create_response.get_json()['id']
        
        # Fetch requirement
        response = client.get(f'/api/new_requirements/{req_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['title'] == 'Detailed Requirement'
        assert 'analysis' in data
        assert data['analysis']['title'] == 'Test Analysis'
    
    def test_get_requirement_not_found(self, client):
        """GET /api/new_requirements/<id> with invalid id should return 404"""
        response = client.get('/api/new_requirements/999999')
        assert response.status_code == 404
    
    def test_update_requirement(self, client):
        """PUT /api/new_requirements/<id> should update requirement"""
        # Setup and create
        project_payload = {
            'project_code': unique_code('REQ'),
            'project_name': 'Update Req Test'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        scenario_response = client.post('/api/scenarios', json={
            'project_id': project_id,
            'name': 'Test'
        })
        scenario_id = scenario_response.get_json()['id']
        
        analysis_response = client.post('/api/analyses', json={
            'scenario_id': scenario_id,
            'title': 'Test'
        })
        analysis_id = analysis_response.get_json()['id']
        
        create_response = client.post('/api/new_requirements', json={
            'analysis_id': analysis_id,
            'title': 'Original Title',
            'classification': 'Gap'
        })
        req_id = create_response.get_json()['id']
        
        # Update requirement
        update_payload = {
            'title': 'Updated Title',
            'status': 'In Review',
            'priority': 'Critical'
        }
        response = client.put(f'/api/new_requirements/{req_id}', json=update_payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        
        # Verify update
        get_response = client.get(f'/api/new_requirements/{req_id}')
        updated_data = get_response.get_json()
        assert updated_data['title'] == 'Updated Title'
        assert updated_data['priority'] == 'Critical'
    
    def test_update_requirement_invalid_classification(self, client):
        """PUT /api/new_requirements/<id> with invalid classification should fail"""
        # Setup and create
        project_payload = {
            'project_code': unique_code('REQ'),
            'project_name': 'Invalid Update Test'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        scenario_response = client.post('/api/scenarios', json={
            'project_id': project_id,
            'name': 'Test'
        })
        scenario_id = scenario_response.get_json()['id']
        
        analysis_response = client.post('/api/analyses', json={
            'scenario_id': scenario_id,
            'title': 'Test'
        })
        analysis_id = analysis_response.get_json()['id']
        
        create_response = client.post('/api/new_requirements', json={
            'analysis_id': analysis_id,
            'title': 'Test',
            'classification': 'Gap'
        })
        req_id = create_response.get_json()['id']
        
        # Try invalid classification
        response = client.put(f'/api/new_requirements/{req_id}', json={
            'classification': 'BadType'
        })
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
    
    def test_update_requirement_not_found(self, client):
        """PUT /api/new_requirements/<id> with invalid id should return 404"""
        response = client.put('/api/new_requirements/999999', json={'title': 'Test'})
        assert response.status_code == 404
    
    def test_delete_requirement_success(self, client):
        """DELETE /api/new_requirements/<id> should delete requirement"""
        # Setup and create
        project_payload = {
            'project_code': unique_code('REQ'),
            'project_name': 'Delete Req Test'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        scenario_response = client.post('/api/scenarios', json={
            'project_id': project_id,
            'name': 'Test'
        })
        scenario_id = scenario_response.get_json()['id']
        
        analysis_response = client.post('/api/analyses', json={
            'scenario_id': scenario_id,
            'title': 'Test'
        })
        analysis_id = analysis_response.get_json()['id']
        
        create_response = client.post('/api/new_requirements', json={
            'analysis_id': analysis_id,
            'title': 'To Be Deleted'
        })
        req_id = create_response.get_json()['id']
        
        # Delete requirement
        response = client.delete(f'/api/new_requirements/{req_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        
        # Verify deletion
        get_response = client.get(f'/api/new_requirements/{req_id}')
        assert get_response.status_code == 404
    
    def test_delete_requirement_not_found(self, client):
        """DELETE /api/new_requirements/<id> with invalid id should return 404"""
        response = client.delete('/api/new_requirements/999999')
        assert response.status_code == 404
    
    def test_convert_fit_to_config(self, client):
        """POST /api/new_requirements/<id>/convert should convert Fit to CONFIG"""
        # Setup complete hierarchy
        project_payload = {
            'project_code': unique_code('CNV'),
            'project_name': 'Conversion Test - Fit'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        scenario_response = client.post('/api/scenarios', json={
            'project_id': project_id,
            'name': 'Config Test Scenario'
        })
        scenario_id = scenario_response.get_json()['id']
        
        analysis_response = client.post('/api/analyses', json={
            'scenario_id': scenario_id,
            'title': 'Fit Analysis'
        })
        analysis_id = analysis_response.get_json()['id']
        
        # Create Fit requirement
        req_response = client.post('/api/new_requirements', json={
            'analysis_id': analysis_id,
            'title': 'Standard approval works',
            'classification': 'Fit',
            'module': 'MM'
        })
        req_id = req_response.get_json()['id']
        
        # Convert requirement
        convert_payload = {
            'config_type': 'Standard',
            'owner': 'Config Team',
            'converted_by': 'test_user'
        }
        response = client.post(f'/api/new_requirements/{req_id}/convert', json=convert_payload)
        assert response.status_code == 201
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['converted_to'] == 'CONFIG'
        assert 'item_id' in data
        assert 'item_code' in data
        
        # Verify requirement updated
        req_check = client.get(f'/api/new_requirements/{req_id}')
        req_data = req_check.get_json()
        assert req_data['conversion_status'] == 'converted'
        assert req_data['converted_item_type'] == 'CONFIG'
        assert req_data['converted_item_id'] == data['item_id']
        
        # Verify config item created
        config_response = client.get(f'/api/config_items?requirement_id={req_id}')
        config_list = config_response.get_json()
        assert len(config_list) >= 1
        assert config_list[0]['requirement_id'] == req_id
        assert config_list[0]['scenario_id'] == scenario_id
    
    def test_convert_gap_to_wricef(self, client):
        """POST /api/new_requirements/<id>/convert should convert Gap to WRICEF"""
        # Setup complete hierarchy
        project_payload = {
            'project_code': unique_code('CNV'),
            'project_name': 'Conversion Test - Gap'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        scenario_response = client.post('/api/scenarios', json={
            'project_id': project_id,
            'name': 'WRICEF Test Scenario'
        })
        scenario_id = scenario_response.get_json()['id']
        
        analysis_response = client.post('/api/analyses', json={
            'scenario_id': scenario_id,
            'title': 'Gap Analysis'
        })
        analysis_id = analysis_response.get_json()['id']
        
        # Create Gap requirement
        req_response = client.post('/api/new_requirements', json={
            'analysis_id': analysis_id,
            'title': 'Custom workflow needed',
            'classification': 'Gap',
            'module': 'SD'
        })
        req_id = req_response.get_json()['id']
        
        # Convert requirement
        convert_payload = {
            'wricef_type': 'Workflow',
            'complexity': 'High',
            'effort_days': 15,
            'owner': 'Dev Team',
            'converted_by': 'test_user'
        }
        response = client.post(f'/api/new_requirements/{req_id}/convert', json=convert_payload)
        assert response.status_code == 201
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['converted_to'] == 'WRICEF'
        assert 'item_id' in data
        
        # Verify requirement updated
        req_check = client.get(f'/api/new_requirements/{req_id}')
        req_data = req_check.get_json()
        assert req_data['conversion_status'] == 'converted'
        assert req_data['converted_item_type'] == 'WRICEF'
        
        # Verify wricef item created
        wricef_response = client.get(f'/api/wricef_items?requirement_id={req_id}')
        wricef_list = wricef_response.get_json()
        assert len(wricef_list) >= 1
        assert wricef_list[0]['requirement_id'] == req_id
        assert wricef_list[0]['scenario_id'] == scenario_id
    
    def test_convert_partialfit_to_wricef(self, client):
        """POST /api/new_requirements/<id>/convert should convert PartialFit to WRICEF"""
        # Setup
        project_payload = {
            'project_code': unique_code('CNV'),
            'project_name': 'Conversion Test - PartialFit'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        scenario_response = client.post('/api/scenarios', json={
            'project_id': project_id,
            'name': 'Test'
        })
        scenario_id = scenario_response.get_json()['id']
        
        analysis_response = client.post('/api/analyses', json={
            'scenario_id': scenario_id,
            'title': 'Test'
        })
        analysis_id = analysis_response.get_json()['id']
        
        # Create PartialFit requirement
        req_response = client.post('/api/new_requirements', json={
            'analysis_id': analysis_id,
            'title': 'Needs enhancement',
            'classification': 'PartialFit'
        })
        req_id = req_response.get_json()['id']
        
        # Convert
        response = client.post(f'/api/new_requirements/{req_id}/convert', json={})
        assert response.status_code == 201
        data = response.get_json()
        assert data['converted_to'] == 'WRICEF'
    
    def test_convert_duplicate_should_fail(self, client):
        """POST /api/new_requirements/<id>/convert on already converted requirement should fail"""
        # Setup and create Fit requirement
        project_payload = {
            'project_code': unique_code('CNV'),
            'project_name': 'Duplicate Conversion Test'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        scenario_response = client.post('/api/scenarios', json={
            'project_id': project_id,
            'name': 'Test'
        })
        scenario_id = scenario_response.get_json()['id']
        
        analysis_response = client.post('/api/analyses', json={
            'scenario_id': scenario_id,
            'title': 'Test'
        })
        analysis_id = analysis_response.get_json()['id']
        
        req_response = client.post('/api/new_requirements', json={
            'analysis_id': analysis_id,
            'title': 'Test',
            'classification': 'Fit'
        })
        req_id = req_response.get_json()['id']
        
        # First conversion - should succeed
        first_response = client.post(f'/api/new_requirements/{req_id}/convert', json={})
        assert first_response.status_code == 201
        
        # Second conversion - should fail
        second_response = client.post(f'/api/new_requirements/{req_id}/convert', json={})
        assert second_response.status_code == 400
        data = second_response.get_json()
        assert 'error' in data
        assert 'already converted' in data['error'].lower()
    
    def test_convert_requirement_not_found(self, client):
        """POST /api/new_requirements/<id>/convert with invalid id should return 404"""
        response = client.post('/api/new_requirements/999999/convert', json={})
        assert response.status_code == 404
    
    def test_delete_converted_requirement_should_fail(self, client):
        """DELETE converted requirement should fail"""
        # Setup and create requirement
        project_payload = {
            'project_code': unique_code('CNV'),
            'project_name': 'Delete Converted Test'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        scenario_response = client.post('/api/scenarios', json={
            'project_id': project_id,
            'name': 'Test'
        })
        scenario_id = scenario_response.get_json()['id']
        
        analysis_response = client.post('/api/analyses', json={
            'scenario_id': scenario_id,
            'title': 'Test'
        })
        analysis_id = analysis_response.get_json()['id']
        
        req_response = client.post('/api/new_requirements', json={
            'analysis_id': analysis_id,
            'title': 'Test',
            'classification': 'Fit'
        })
        req_id = req_response.get_json()['id']
        
        # Convert requirement
        client.post(f'/api/new_requirements/{req_id}/convert', json={})
        
        # Try to delete - should fail
        delete_response = client.delete(f'/api/new_requirements/{req_id}')
        assert delete_response.status_code == 400
        data = delete_response.get_json()
        assert 'error' in data
        assert 'converted' in data['error'].lower()


# ============== CONVERT TO UNIT TEST API TESTS ==============
class TestConvertToUnitTestAPI:
    """Tests for converting WRICEF/CONFIG items to Unit Tests"""
    
    def test_convert_wricef_to_unit_test(self, client):
        """POST /api/wricef_items/<id>/convert-to-unit-test should create unit test"""
        # Setup hierarchy
        project_payload = {
            'project_code': unique_code('WUNIT'),
            'project_name': 'WRICEF Unit Test Conversion'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        scenario_response = client.post('/api/scenarios', json={
            'project_id': project_id,
            'name': 'Test Scenario'
        })
        scenario_id = scenario_response.get_json()['id']
        
        analysis_response = client.post('/api/analyses', json={
            'scenario_id': scenario_id,
            'title': 'Gap Analysis'
        })
        analysis_id = analysis_response.get_json()['id']
        
        # Create Gap requirement
        req_response = client.post('/api/new_requirements', json={
            'analysis_id': analysis_id,
            'title': 'Custom workflow needed',
            'classification': 'Gap',
            'module': 'FI'
        })
        req_id = req_response.get_json()['id']
        
        # Convert to WRICEF
        wricef_response = client.post(f'/api/new_requirements/{req_id}/convert', json={
            'wricef_type': 'Enhancement',
            'complexity': 'High',
            'effort_days': 10,
            'owner': 'Dev Team'
        })
        assert wricef_response.status_code == 201
        wricef_id = wricef_response.get_json()['item_id']
        
        # Convert WRICEF to Unit Test
        test_payload = {
            'owner': 'QA Team',
            'status': 'Active'
        }
        response = client.post(f'/api/wricef_items/{wricef_id}/convert-to-unit-test', json=test_payload)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'test_id' in data
        assert 'test_code' in data
        assert data['message'] == 'WRICEF item successfully converted to Unit Test'
        
        # Verify test was created
        test_id = data['test_id']
        test_response = client.get(f'/api/test_management/{test_id}')
        assert test_response.status_code == 200
        test_data = test_response.get_json()
        
        assert test_data['project_id'] == project_id
        assert test_data['test_type'] == 'Unit'
        assert 'Unit Test:' in test_data['title']
        assert test_data['source_type'] == 'WRICEF'
        assert test_data['source_id'] == wricef_id
        assert test_data['owner'] == 'QA Team'
        assert test_data['status'] == 'Active'
    
    def test_convert_config_to_unit_test(self, client):
        """POST /api/config_items/<id>/convert-to-unit-test should create unit test"""
        # Setup hierarchy
        project_payload = {
            'project_code': unique_code('CUNIT'),
            'project_name': 'CONFIG Unit Test Conversion'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        scenario_response = client.post('/api/scenarios', json={
            'project_id': project_id,
            'name': 'Test Scenario'
        })
        scenario_id = scenario_response.get_json()['id']
        
        analysis_response = client.post('/api/analyses', json={
            'scenario_id': scenario_id,
            'title': 'Fit Analysis'
        })
        analysis_id = analysis_response.get_json()['id']
        
        # Create Fit requirement
        req_response = client.post('/api/new_requirements', json={
            'analysis_id': analysis_id,
            'title': 'Standard approval process',
            'classification': 'Fit',
            'module': 'MM'
        })
        req_id = req_response.get_json()['id']
        
        # Convert to CONFIG
        config_response = client.post(f'/api/new_requirements/{req_id}/convert', json={
            'config_type': 'Standard',
            'owner': 'Config Team'
        })
        assert config_response.status_code == 201
        config_id = config_response.get_json()['item_id']
        
        # Convert CONFIG to Unit Test
        test_payload = {
            'owner': 'Test Team',
            'status': 'Draft'
        }
        response = client.post(f'/api/config_items/{config_id}/convert-to-unit-test', json=test_payload)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'test_id' in data
        assert 'test_code' in data
        assert data['message'] == 'CONFIG item successfully converted to Unit Test'
        
        # Verify test was created
        test_id = data['test_id']
        test_response = client.get(f'/api/test_management/{test_id}')
        assert test_response.status_code == 200
        test_data = test_response.get_json()
        
        assert test_data['project_id'] == project_id
        assert test_data['test_type'] == 'Unit'
        assert 'Unit Test:' in test_data['title']
        assert test_data['source_type'] == 'CONFIG'
        assert test_data['source_id'] == config_id
        assert test_data['owner'] == 'Test Team'
        assert test_data['status'] == 'Draft'
    
    def test_convert_wricef_not_found(self, client):
        """Converting non-existent WRICEF should return 404"""
        response = client.post('/api/wricef_items/99999/convert-to-unit-test', json={})
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
        assert 'not found' in data['error'].lower()
    
    def test_convert_config_not_found(self, client):
        """Converting non-existent CONFIG should return 404"""
        response = client.post('/api/config_items/99999/convert-to-unit-test', json={})
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
        assert 'not found' in data['error'].lower()
    
    def test_convert_wricef_with_unit_test_steps(self, client):
        """Unit test steps should be copied from WRICEF to test_management"""
        import json
        
        # Setup hierarchy
        project_payload = {
            'project_code': unique_code('WSTEP'),
            'project_name': 'WRICEF Steps Test'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        scenario_response = client.post('/api/scenarios', json={
            'project_id': project_id,
            'name': 'Test Scenario'
        })
        scenario_id = scenario_response.get_json()['id']
        
        analysis_response = client.post('/api/analyses', json={
            'scenario_id': scenario_id,
            'title': 'Analysis'
        })
        analysis_id = analysis_response.get_json()['id']
        
        req_response = client.post('/api/new_requirements', json={
            'analysis_id': analysis_id,
            'title': 'Requirement',
            'classification': 'Gap'
        })
        req_id = req_response.get_json()['id']
        
        # Convert to WRICEF
        wricef_response = client.post(f'/api/new_requirements/{req_id}/convert', json={})
        wricef_id = wricef_response.get_json()['item_id']
        
        # Update WRICEF with unit test steps
        test_steps = [
            {"step": "1", "action": "Navigate to screen", "expected": "Screen loads"},
            {"step": "2", "action": "Enter data", "expected": "Data validated"}
        ]
        update_response = client.put(f'/api/wricef_items/{wricef_id}', json={
            'title': 'Updated WRICEF',
            'unit_test_steps': json.dumps(test_steps)
        })
        
        # Convert to Unit Test
        response = client.post(f'/api/wricef_items/{wricef_id}/convert-to-unit-test', json={})
        assert response.status_code == 201
        test_id = response.get_json()['test_id']
        
        # Verify steps were copied
        test_response = client.get(f'/api/test_management/{test_id}')
        test_data = test_response.get_json()
        steps_from_test = json.loads(test_data['steps'])
        
        assert len(steps_from_test) == 2
        assert steps_from_test[0]['action'] == 'Navigate to screen'
        assert steps_from_test[1]['expected'] == 'Data validated'


# ============== TEST MANAGEMENT API TESTS (Epic D) ==============
class TestTestManagementAPI:
    """Tests for Test Management expansion with test_type filtering and scenario-based creation"""
    
    def test_get_tests_with_test_type_filter(self, client):
        """GET /api/test_management?test_type=Unit should filter by test type"""
        # Create project
        project_payload = {
            'project_code': unique_code('TFILT'),
            'project_name': 'Test Type Filtering'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        # Create different test types
        test_types = ['Unit', 'SIT', 'UAT', 'String', 'Sprint']
        for test_type in test_types:
            client.post('/api/test_management', json={
                'project_id': project_id,
                'test_type': test_type,
                'title': f'{test_type} Test',
                'description': f'Test for {test_type}'
            })
        
        # Filter by Unit tests
        response = client.get(f'/api/test_management?project_id={project_id}&test_type=Unit')
        assert response.status_code == 200
        data = response.get_json()
        
        assert len(data) == 1
        assert data[0]['test_type'] == 'Unit'
        assert data[0]['title'] == 'Unit Test'
        
        # Filter by UAT tests
        response = client.get(f'/api/test_management?project_id={project_id}&test_type=UAT')
        assert response.status_code == 200
        data = response.get_json()
        
        assert len(data) == 1
        assert data[0]['test_type'] == 'UAT'
        assert data[0]['title'] == 'UAT Test'
        
        # Get all tests (no filter)
        response = client.get(f'/api/test_management?project_id={project_id}')
        assert response.status_code == 200
        data = response.get_json()
        
        assert len(data) == 5
    
    def test_create_sit_test_from_scenario(self, client):
        """POST /api/scenarios/:id/create-test should create SIT test"""
        # Setup hierarchy
        project_payload = {
            'project_code': unique_code('SIT'),
            'project_name': 'SIT Test Creation'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        scenario_response = client.post('/api/scenarios', json={
            'project_id': project_id,
            'name': 'Purchase Order Processing',
            'description': 'End-to-end PO process'
        })
        scenario_id = scenario_response.get_json()['id']
        
        # Create SIT test from scenario
        test_payload = {
            'test_type': 'SIT',
            'owner': 'Test Team',
            'status': 'Active'
        }
        response = client.post(f'/api/scenarios/{scenario_id}/create-test', json=test_payload)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'test_id' in data
        assert 'test_code' in data
        assert data['test_type'] == 'SIT'
        assert data['scenario_details']['main_scenario'] == 'Purchase Order Processing'
        
        # Verify test was created
        test_id = data['test_id']
        test_response = client.get(f'/api/test_management/{test_id}')
        assert test_response.status_code == 200
        test_data = test_response.get_json()
        
        assert test_data['project_id'] == project_id
        assert test_data['test_type'] == 'SIT'
        assert 'SIT Test:' in test_data['title']
        assert 'Purchase Order Processing' in test_data['title']
        assert test_data['source_type'] == 'SCENARIO'
        assert test_data['source_id'] == scenario_id
        assert test_data['owner'] == 'Test Team'
        assert test_data['status'] == 'Active'
    
    def test_create_uat_test_from_composite_scenario(self, client):
        """POST /api/scenarios/:id/create-test for composite should expand included scenarios"""
        # Setup hierarchy
        project_payload = {
            'project_code': unique_code('UAT'),
            'project_name': 'UAT Composite Test'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        # Create base scenarios
        scenario1_response = client.post('/api/scenarios', json={
            'project_id': project_id,
            'name': 'Create PO'
        })
        scenario1_id = scenario1_response.get_json()['id']
        
        scenario2_response = client.post('/api/scenarios', json={
            'project_id': project_id,
            'name': 'Approve PO'
        })
        scenario2_id = scenario2_response.get_json()['id']
        
        scenario3_response = client.post('/api/scenarios', json={
            'project_id': project_id,
            'name': 'Receive Goods'
        })
        scenario3_id = scenario3_response.get_json()['id']
        
        # Create composite scenario
        composite_response = client.post('/api/scenarios', json={
            'project_id': project_id,
            'name': 'Complete Procurement Process',
            'is_composite': True,
            'included_scenario_ids': [scenario1_id, scenario2_id, scenario3_id]
        })
        composite_id = composite_response.get_json()['id']
        
        # Create UAT test from composite scenario
        test_payload = {
            'test_type': 'UAT',
            'owner': 'Business Team',
            'status': 'Draft'
        }
        response = client.post(f'/api/scenarios/{composite_id}/create-test', json=test_payload)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['test_type'] == 'UAT'
        
        # Verify composite expansion
        assert data['scenario_details']['is_composite'] == True
        assert data['scenario_details']['main_scenario'] == 'Complete Procurement Process'
        assert 'included_scenarios' in data['scenario_details']
        assert len(data['scenario_details']['included_scenarios']) == 3
        
        # Verify test was created with composite details
        test_id = data['test_id']
        test_response = client.get(f'/api/test_management/{test_id}')
        test_data = test_response.get_json()
        
        assert test_data['test_type'] == 'UAT'
        assert 'Composite Test Coverage' in test_data['description']
        assert 'Create PO' in test_data['description']
        assert 'Approve PO' in test_data['description']
        assert 'Receive Goods' in test_data['description']
    
    def test_create_test_invalid_type(self, client):
        """Creating test with invalid test_type should fail"""
        project_payload = {
            'project_code': unique_code('INV'),
            'project_name': 'Invalid Test'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        scenario_response = client.post('/api/scenarios', json={
            'project_id': project_id,
            'name': 'Test Scenario'
        })
        scenario_id = scenario_response.get_json()['id']
        
        # Try invalid test type
        response = client.post(f'/api/scenarios/{scenario_id}/create-test', json={
            'test_type': 'INVALID_TYPE'
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'Invalid test_type' in data['error']
    
    def test_create_test_scenario_not_found(self, client):
        """Creating test from non-existent scenario should fail"""
        response = client.post('/api/scenarios/99999/create-test', json={
            'test_type': 'SIT'
        })
        
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
        assert 'not found' in data['error'].lower()
    
    def test_create_performance_test_from_scenario(self, client):
        """POST /api/scenarios/:id/create-test with PerformanceLoad type"""
        project_payload = {
            'project_code': unique_code('PERF'),
            'project_name': 'Performance Testing'
        }
        project_response = client.post('/api/projects', json=project_payload)
        project_id = project_response.get_json()['id']
        
        scenario_response = client.post('/api/scenarios', json={
            'project_id': project_id,
            'name': 'High Volume Order Processing'
        })
        scenario_id = scenario_response.get_json()['id']
        
        # Create PerformanceLoad test
        response = client.post(f'/api/scenarios/{scenario_id}/create-test', json={
            'test_type': 'PerformanceLoad',
            'owner': 'Performance Team'
        })
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['test_type'] == 'PerformanceLoad'
        
        test_id = data['test_id']
        test_response = client.get(f'/api/test_management/{test_id}')
        test_data = test_response.get_json()
        
        assert test_data['test_type'] == 'PerformanceLoad'
        assert 'PerformanceLoad Test:' in test_data['title']

