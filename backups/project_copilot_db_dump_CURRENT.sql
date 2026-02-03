PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE requirements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,          -- Örn: FS_MM_041
            title TEXT NOT NULL,         -- Örn: PO Approval Workflow
            module TEXT,                 -- Örn: MM, SD, FI
            complexity TEXT,             -- Low, Medium, High
            status TEXT DEFAULT 'Draft', -- Draft, Ready, In Progress
            ai_status TEXT DEFAULT 'None', -- None, Draft, Full
            summary TEXT,                -- AI tarafından üretilen özet
            tech_spec TEXT,              -- AI tarafından üretilen teknik detay
            effort_days INTEGER          -- Tahmini efor
        , project_id INTEGER);
INSERT INTO requirements VALUES(1,'FS_MM_041','Purchase Order Approval Workflow','MM','Medium','In Progress','Draft',NULL,NULL,8,NULL);
INSERT INTO requirements VALUES(2,'FS_SD_012','Sales Order Output Management','SD','Low','Ready','Full',NULL,NULL,3,NULL);
INSERT INTO requirements VALUES(3,'Wricef_SD_Test','SD_Test_Order','SD','Low','Draft','None',NULL,NULL,NULL,NULL);
INSERT INTO requirements VALUES(4,'test','test2','MM','Low','Draft','None',NULL,NULL,NULL,NULL);
INSERT INTO requirements VALUES(5,'test2','test2','SD','Low','Draft','None',NULL,NULL,NULL,NULL);
INSERT INTO requirements VALUES(6,'Wricef_02302','Sales ORder kadslkasd','FI','Medium','Draft','None',NULL,NULL,NULL,NULL);
INSERT INTO requirements VALUES(7,'sdfsdf','sdfsdf','MM','High','Draft','None',NULL,NULL,NULL,2);
INSERT INTO requirements VALUES(8,'asdaksdşlak','asdşlakdsşlaksd','FI','Medium','Draft','None',NULL,NULL,NULL,2);
INSERT INTO requirements VALUES(9,'Deneme Acme','Denedm','FI','Medium','Draft','None',NULL,NULL,NULL,1);
INSERT INTO requirements VALUES(10,'Wricef AI','Sales Order','SD','Low','Draft','None',NULL,NULL,NULL,1);
CREATE TABLE projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_code TEXT NOT NULL,
            project_name TEXT NOT NULL,
            customer_name TEXT,
            start_date DATE,
            end_date DATE,
            status TEXT DEFAULT 'Planning',
            modules TEXT,
            environment TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
INSERT INTO projects VALUES(1,'PRJ-2026-001','ACME Corp S/4HANA Migration','ACME Corporation',NULL,NULL,'Active','MM,SD,FI,CO','DEV',NULL,'2026-01-31 01:49:38');
INSERT INTO projects VALUES(2,'PRJ-2026-002','Global Corp ERP Modernization','Global Corporation',NULL,NULL,'Planning','FI,CO,HR,PP',NULL,NULL,'2026-01-31 02:40:31');
CREATE TABLE analysis_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            session_name TEXT NOT NULL,
            module TEXT,
            process_name TEXT,
            session_date DATE,
            facilitator TEXT,
            status TEXT DEFAULT 'Planned',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );
INSERT INTO analysis_sessions VALUES(1,2,'MM Workshop','MM',NULL,NULL,NULL,'Planned',NULL,'2026-01-31 12:01:34');
INSERT INTO analysis_sessions VALUES(2,2,'FI Workshop - General Ledger','FI',NULL,NULL,NULL,'Planned',NULL,'2026-01-31 12:18:28');
INSERT INTO analysis_sessions VALUES(3,1,'SD Workshop','SD',NULL,NULL,NULL,'Planned',NULL,'2026-01-31 12:19:03');
INSERT INTO analysis_sessions VALUES(4,2,'FI Deneme 2','FI',NULL,NULL,NULL,'Planned',NULL,'2026-01-31 14:49:15');
INSERT INTO analysis_sessions VALUES(5,1,'sdsad','FI',NULL,NULL,NULL,'Planned',NULL,'2026-02-01 10:08:23');
INSERT INTO analysis_sessions VALUES(6,1,'MM WS','MM','P2P',NULL,NULL,'Planned',NULL,'2026-02-01 15:11:07');
CREATE TABLE questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            category TEXT,
            question_order INTEGER,
            is_mandatory INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES analysis_sessions(id)
        );
INSERT INTO questions VALUES(1,3,'asdasd',NULL,NULL,0,'2026-01-31 15:14:22');
INSERT INTO questions VALUES(2,3,'sdfldsfişlsdf',NULL,NULL,0,'2026-01-31 15:14:33');
INSERT INTO questions VALUES(3,3,'aösdmasdlşadksaşlsd',NULL,NULL,0,'2026-01-31 15:15:17');
INSERT INTO questions VALUES(4,6,'lsjlksjlksjs',NULL,NULL,0,'2026-02-01 15:11:25');
CREATE TABLE answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER NOT NULL,
            answer_text TEXT,
            answered_by TEXT,
            answered_at TIMESTAMP,
            confidence_score REAL,
            FOREIGN KEY (question_id) REFERENCES questions(id)
        );
INSERT INTO answers VALUES(1,1,'asdadasd',NULL,'2026-01-31 15:14:22',NULL);
INSERT INTO answers VALUES(2,2,'sdişflfşilsdşiflşsilfişdsf',NULL,'2026-01-31 15:14:33',NULL);
INSERT INTO answers VALUES(3,3,'asdşasldiaşsdlşadlasda',NULL,'2026-01-31 15:15:17',NULL);
INSERT INTO answers VALUES(4,4,'lksjlksjkljs',NULL,'2026-02-01 15:11:25',NULL);
CREATE TABLE fitgap (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            gap_id TEXT NOT NULL,
            process_name TEXT,
            gap_description TEXT,
            impact_area TEXT,
            solution_type TEXT,
            risk_level TEXT,
            effort_estimate INTEGER,
            priority TEXT DEFAULT 'Medium',
            status TEXT DEFAULT 'Identified',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES analysis_sessions(id)
        );
INSERT INTO fitgap VALUES(1,4,'Gap1',NULL,NULL,NULL,NULL,NULL,NULL,'High','Identified',NULL,'2026-01-31 14:49:50');
INSERT INTO fitgap VALUES(2,4,'Gap1',NULL,NULL,NULL,NULL,NULL,NULL,'High','Identified',NULL,'2026-01-31 14:49:50');
INSERT INTO fitgap VALUES(3,4,'Gap1',NULL,NULL,NULL,NULL,NULL,NULL,'High','Identified',NULL,'2026-01-31 14:49:50');
INSERT INTO fitgap VALUES(4,4,'Gap2',NULL,NULL,NULL,NULL,NULL,NULL,'Low','Identified',NULL,'2026-01-31 14:50:04');
INSERT INTO fitgap VALUES(5,3,'gap001',NULL,NULL,NULL,NULL,NULL,NULL,'Medium','Identified',NULL,'2026-01-31 15:14:49');
INSERT INTO fitgap VALUES(6,3,'gap002',NULL,NULL,NULL,NULL,NULL,NULL,'Medium','Identified',NULL,'2026-01-31 15:15:04');
INSERT INTO fitgap VALUES(7,4,'gap3',NULL,'asdasşdliadlsş',NULL,'Configuration',NULL,NULL,'Medium','Identified',NULL,'2026-02-01 08:36:29');
INSERT INTO fitgap VALUES(8,3,'gap9',NULL,'ıııııkklklklkllkklk',NULL,'Configuration',NULL,NULL,'Low','Identified',NULL,'2026-02-01 09:03:41');
INSERT INTO fitgap VALUES(9,6,'gap001',NULL,'lkjslkjslk',NULL,'Development',NULL,NULL,'Medium','Identified',NULL,'2026-02-01 15:11:40');
INSERT INTO fitgap VALUES(10,6,'GAP AI',NULL,'Custom approval workflow needed for PO amounts exceeding 10,000 EUR',NULL,'Configuration',NULL,NULL,'Medium','Identified',NULL,'2026-02-01 19:49:53');
CREATE TABLE fs_ts_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            requirement_id INTEGER NOT NULL,
            document_type TEXT,
            version TEXT DEFAULT '1.0',
            content TEXT,
            template_used TEXT,
            status TEXT DEFAULT 'Draft',
            approved_by TEXT,
            approved_at TIMESTAMP,
            file_path TEXT,
            sharepoint_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (requirement_id) REFERENCES requirements(id)
        );
INSERT INTO fs_ts_documents VALUES(1,9,'FS','1.0','','SAP Activate','Draft',NULL,NULL,NULL,NULL,'2026-02-01 18:33:32','2026-02-01 18:33:32');
INSERT INTO fs_ts_documents VALUES(2,10,'FS','1.0','','Standard','Draft',NULL,NULL,NULL,NULL,'2026-02-01 19:42:15','2026-02-01 19:42:15');
INSERT INTO fs_ts_documents VALUES(3,9,'TS','1.0',replace('# Technical Specification\n## Deneme Acme - Denedm\n\n### 1. Technical Overview\n- **Development Type:** Enhancement\n- **Package:** ZMM_CUSTOM\n- **Transport:** To be assigned\n\n### 2. Development Objects\n\n#### 2.1 Custom Tables\n```\nTable: ZMM_CUSTOM_DATA\nFields:\n  - MANDT (Client)\n  - DOCNR (Document Number) - Key\n  - BUKRS (Company Code)\n  - ERDAT (Created Date)\n  - ERNAM (Created By)\n  - STATUS (Status)\n```\n\n#### 2.2 Function Modules\n```abap\nFUNCTION Z_MM_PROCESS_DATA\n  IMPORTING\n    IV_DOCNR TYPE ZDOCNR\n    IV_BUKRS TYPE BUKRS\n  EXPORTING\n    EV_STATUS TYPE ZSTATUS\n  EXCEPTIONS\n    NOT_FOUND\n    INVALID_INPUT.\n```\n\n### 3. Implementation Details\n\n#### 3.1 Main Logic (Pseudo-code)\n```abap\nMETHOD process_document.\n  " 1. Validate input\n  IF iv_docnr IS INITIAL.\n    RAISE EXCEPTION invalid_input.\n  ENDIF.\n  \n  " 2. Read master data\n  SELECT SINGLE * FROM zmm_custom_data\n    INTO @DATA(ls_data)\n    WHERE docnr = @iv_docnr.\n    \n  " 3. Execute business logic\n  CASE ls_data-status.\n    WHEN ''01''. " New\n      perform_initial_processing( ).\n    WHEN ''02''. " In Process\n      perform_update_processing( ).\n  ENDCASE.\n  \n  " 4. Update status\n  UPDATE zmm_custom_data\n    SET status = ''03''\n    WHERE docnr = iv_docnr.\nENDMETHOD.\n```\n\n### 4. Error Handling\n| Error Code | Message | Action |\n|------------|---------|--------|\n| 001 | Document not found | Display error, return |\n| 002 | Invalid status | Log warning, skip |\n| 003 | Authorization failed | Raise exception |\n\n### 5. Performance Considerations\n- Use buffered tables where possible\n- Implement parallel processing for mass operations\n- Add appropriate indexes\n\n### 6. Unit Test Cases\n- Test Case 1: Valid document processing\n- Test Case 2: Invalid input handling\n- Test Case 3: Authorization check\n\n---\n*Generated by AI Co-Pilot*\n','\n',char(10)),'Standard','Draft',NULL,NULL,NULL,NULL,'2026-02-01 19:45:04','2026-02-01 19:46:03');
CREATE TABLE test_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fs_ts_id INTEGER NOT NULL,
            test_case_id TEXT NOT NULL,
            test_scenario TEXT,
            test_type TEXT,
            preconditions TEXT,
            test_steps TEXT,
            expected_result TEXT,
            status TEXT DEFAULT 'Not Started',
            environment TEXT,
            executed_by TEXT,
            executed_at TIMESTAMP,
            alm_reference TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (fs_ts_id) REFERENCES fs_ts_documents(id)
        );
INSERT INTO test_cases VALUES(1,1,'123123','işclasidşglişdsflgsd','Unit','sdflsişdfls','isdşflisşdf','sidflisşdfls','Not Started',NULL,'Current User','2026-02-01 19:07:18',NULL,'2026-02-01 19:06:36');
INSERT INTO test_cases VALUES(2,2,'TC-MM-001','Verify PO approval triggers for amounts > 10K','UAT','User has MM authorization','Create PO with ME21N\n2. Enter amount 15,000\n3. Save','Workflow task created for manager','Passed',NULL,'Current User','2026-02-01 19:51:28',NULL,'2026-02-01 19:51:18');
CREATE TABLE audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT NOT NULL,
            record_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            old_values TEXT,
            new_values TEXT,
            changed_by TEXT,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
DELETE FROM sqlite_sequence;
INSERT INTO sqlite_sequence VALUES('requirements',10);
INSERT INTO sqlite_sequence VALUES('projects',2);
INSERT INTO sqlite_sequence VALUES('analysis_sessions',6);
INSERT INTO sqlite_sequence VALUES('fitgap',10);
INSERT INTO sqlite_sequence VALUES('questions',4);
INSERT INTO sqlite_sequence VALUES('answers',4);
INSERT INTO sqlite_sequence VALUES('fs_ts_documents',3);
INSERT INTO sqlite_sequence VALUES('test_cases',2);
COMMIT;
