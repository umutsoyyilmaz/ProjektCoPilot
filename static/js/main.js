// Main client JS (extracted from template + safety & a11y overrides)
// NOTE: this file re-implements the original inline app logic and adds XSS prevention,
// accessible modal handlers (focus trap & ESC), and keyboard-friendly table rows.

// ============== GLOBAL ==================
let globalProjectId = localStorage.getItem('selectedProjectId') || null;
let currentSessionId = null;
let currentFilter = { module: '', status: '', search: '' };
let previouslyFocusedElement = null;

const hasDOMPurify = typeof DOMPurify !== 'undefined';
function sanitizeHtml(html) {
    if(!html) return '';
    if(hasDOMPurify) return DOMPurify.sanitize(html);
    // fallback: very basic escape
    return html.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function showToast(msg) {
    const t = document.getElementById('toast');
    if(!t) return;
    document.getElementById('toast-msg').innerText = msg;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 3000);
}

// ============== MODAL ACCESSIBILITY HELPERS ==============
function trapFocus(modal) {
    const focusable = modal.querySelectorAll('a[href], button, textarea, input, select, [tabindex]:not([tabindex="-1"])');
    if(!focusable.length) return () => {};
    let first = focusable[0];
    let last = focusable[focusable.length -1];

    function keyListener(e) {
        if(e.key === 'Tab') {
            if(e.shiftKey && document.activeElement === first) {
                e.preventDefault(); last.focus();
            } else if(!e.shiftKey && document.activeElement === last) {
                e.preventDefault(); first.focus();
            }
        } else if(e.key === 'Escape') {
            // close modal
            closeModal(modal.id);
        }
    }

    modal.addEventListener('keydown', keyListener);

    return () => modal.removeEventListener('keydown', keyListener);
}

function openModal(id) {
    const modal = document.getElementById(id);
    if(!modal) return;
    previouslyFocusedElement = document.activeElement;
    modal.style.display = 'block';
    modal.setAttribute('aria-hidden','false');
    // overlay handling (if present)
    const overlay = document.querySelector(`#${id} ~ .modal-overlay, .modal-overlay[onclick*='${id}']`);
    if(overlay) overlay.style.display = 'block';

    // focus first focusable element
    const focusable = modal.querySelectorAll('a[href], button, textarea, input, select, [tabindex]:not([tabindex="-1"])');
    if(focusable.length) focusable[0].focus();

    // trap focus
    modal._releaseTrap = trapFocus(modal);
}

function closeModal(id) {
    const modal = document.getElementById(id);
    if(!modal) return;
    modal.style.display = 'none';
    modal.setAttribute('aria-hidden','true');
    const overlay = document.querySelector(`#${id} ~ .modal-overlay, .modal-overlay[onclick*='${id}']`);
    if(overlay) overlay.style.display = 'none';

    if(modal._releaseTrap) modal._releaseTrap();
    if(previouslyFocusedElement && typeof previouslyFocusedElement.focus === 'function') previouslyFocusedElement.focus();
}

// Override built-in modal open/close functions used inline in template
window.openNewProjectModal = function() { openModal('newProjectModal'); };
window.closeNewProjectModal = function() { closeModal('newProjectModal'); };
window.openNewSessionModal = function() { if(!globalProjectId) { alert('Please select a project from the header first!'); return; } openModal('newSessionModal'); };
window.closeNewSessionModal = function() { closeModal('newSessionModal'); };
window.openAddQuestionModal = function() { openModal('addQuestionModal'); };
window.closeAddQuestionModal = function() { closeModal('addQuestionModal'); };
window.openAddGapModal = function() { openModal('addGapModal'); };
window.closeAddGapModal = function() { closeModal('addGapModal'); };
window.openNewDocumentModal = function() { if(!globalProjectId) { alert('Please select a project first!'); return; } openModal('newDocumentModal'); loadRequirementsForDocModal(); };
window.closeNewDocumentModal = function() { closeModal('newDocumentModal'); };
window.openNewTestCaseModal = function() { if(!globalProjectId) { alert('Please select a project first!'); return; } openModal('newTestCaseModal'); loadDocumentsForTestModal(); };
window.closeNewTestCaseModal = function() { closeModal('newTestCaseModal'); };

// Add ESC key global listener to close currently open modal if any
document.addEventListener('keydown', (e) => {
    if(e.key !== 'Escape') return;
    const openModalEl = document.querySelector('[role="dialog"][style*="display:block"]');
    if(openModalEl) closeModal(openModalEl.id);
});

// Ensure modal overlays close modals via click (they already call inline; this ensures accessibility for click handlers)
document.addEventListener('click', (e) => {
    if(e.target.classList && e.target.classList.contains('modal-overlay')) {
        // find previous sibling modal
        const prev = e.target.previousElementSibling;
        if(prev && prev.hasAttribute && prev.hasAttribute('role') && prev.getAttribute('role') === 'dialog') {
            closeModal(prev.id);
        }
    }
}, true);

// ============== SAFER RENDER HELPERS ==============
function clearChildren(el) { while(el && el.firstChild) el.removeChild(el.firstChild); }

function createCell(text, tag='td', className) {
    const td = document.createElement(tag);
    if(className) td.className = className;
    td.textContent = text != null ? text : '-';
    return td;
}

function createPill(text, pillClass) {
    const s = document.createElement('span');
    s.className = `pill ${pillClass}`;
    s.textContent = text || '-';
    return s;
}

// ============== LOADERS (safe DOM rendering) ==============
window.initializeApp = async function() {
    await loadGlobalProjectDropdown();
    if(globalProjectId) {
        const select = document.getElementById('globalProjectSelect');
        if(select) select.value = globalProjectId;
        await updateProjectStatus();
    }
    navTo('dashboard');
};

window.loadGlobalProjectDropdown = async function() {
    try {
        const response = await fetch('/api/projects');
        const projects = await response.json();
        const select = document.getElementById('globalProjectSelect');
        if(!select) return;
        clearChildren(select);
        const defaultOpt = document.createElement('option'); defaultOpt.value = ''; defaultOpt.textContent = '-- Select Project --';
        select.appendChild(defaultOpt);
        projects.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.id;
            opt.textContent = `${p.project_code} - ${p.project_name}`;
            select.appendChild(opt);
        });
    } catch(err) { console.error('Error loading projects:', err); }
};

window.onGlobalProjectChange = async function() {
    const select = document.getElementById('globalProjectSelect');
    globalProjectId = select.value;

    if(!globalProjectId) {
        localStorage.removeItem('selectedProjectId');
        document.getElementById('globalProjectStatus').style.display = 'none';
    } else {
        localStorage.setItem('selectedProjectId', globalProjectId);
        await updateProjectStatus();
        showToast('Project selected!');
    }
    refreshCurrentView();
};

window.updateProjectStatus = async function() {
    const statusBadge = document.getElementById('globalProjectStatus');
    if(!statusBadge || !globalProjectId) return;
    try {
        const response = await fetch(`/api/projects/${globalProjectId}`);
        const project = await response.json();
        statusBadge.textContent = project.status;
        statusBadge.className = `pill ${project.status === 'Active' ? 'green' : 'blue'}`;
        statusBadge.style.display = 'inline-flex';
    } catch(err) { console.error(err); }
};

// Navigation and many loader placeholders are kept as-is but table rendering switched to DOM
window.navTo = function(viewId, navEl) {
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    if(navEl) navEl.classList.add('active');
    else {
        const items = document.querySelectorAll('.nav-item');
        const mapping = { 'dashboard': 0, 'analysis': 1, 'requirements': 2, 'design': 3, 'testing': 4, 'projects': 5, 'config': 6 };
        if(mapping[viewId] !== undefined && items[mapping[viewId]]) items[mapping[viewId]].classList.add('active');
    }
    document.querySelectorAll('.view').forEach(el => el.classList.remove('active'));
    const target = document.getElementById('view-' + viewId);
    if(target) target.classList.add('active');

    if(viewId === 'dashboard') loadDashboardStats();
    if(viewId === 'requirements') loadRequirements();
    if(viewId === 'analysis') { loadSessionsForGlobalProject(); loadAnalysisStats(); }
    if(viewId === 'projects') loadProjects();
    if(viewId === 'design') loadDocuments();
    if(viewId === 'testing') loadTestCases();
};

window.loadDashboardStats = async function() {
    try {
        let url = '/api/dashboard/stats';
        if(globalProjectId) url += `?project_id=${globalProjectId}`;
        const response = await fetch(url);
        const data = await response.json();
        const subtitleEl = document.querySelector('#view-dashboard .page-subtitle');
        if(subtitleEl) subtitleEl.textContent = (globalProjectId && data.project_name) ? `Project: ${data.project_name} - ${data.project_status}` : 'Select a project from header to see project-specific data';
        document.querySelector('.stat-projects') && (document.querySelector('.stat-projects').textContent = data.total_projects || 0);
        document.querySelector('.stat-gaps') && (document.querySelector('.stat-gaps').textContent = data.total_gaps || 0);
        document.querySelector('.stat-sessions') && (document.querySelector('.stat-sessions').textContent = data.total_sessions || 0);
        document.querySelector('.stat-questions') && (document.querySelector('.stat-questions').textContent = data.total_questions || 0);

        const tbody = document.querySelector('#view-dashboard .smart-table tbody');
        clearChildren(tbody);
        if(data.recent_activities && data.recent_activities.length>0) {
            data.recent_activities.forEach(act => {
                const tr = document.createElement('tr');
                tr.tabIndex = 0; tr.setAttribute('role','button');
                tr.addEventListener('click', () => openSession(act.id));
                tr.addEventListener('keydown', (e) => { if(e.key === 'Enter' || e.key === ' ') openSession(act.id); });
                tr.appendChild(createCell(act.session_name, 'td')); const m = document.createElement('td'); m.appendChild(createPill(act.module || '-', 'blue')); tr.appendChild(m);
                const s = document.createElement('td'); s.appendChild(createPill(act.status, act.status === 'Completed' ? 'green' : 'orange')); tr.appendChild(s);
                tr.appendChild(createCell(act.created_at ? 'Recently' : '-', 'td'));
                tbody.appendChild(tr);
            });
        } else {
            const tr = document.createElement('tr'); tr.appendChild(createCell('No recent activities','td','')); tr.firstChild.setAttribute('colspan',4); tr.firstChild.style.textAlign='center'; tr.firstChild.style.color='#999'; tbody.appendChild(tr);
        }
    } catch(err) { console.error('Dashboard error', err); }
};

// Projects
window.loadProjects = async function() {
    try {
        const response = await fetch('/api/projects');
        const projects = await response.json();
        const tbody = document.getElementById('projects-table-body'); if(!tbody) return;
        clearChildren(tbody);
        if(projects.length === 0) { const tr = document.createElement('tr'); const td = createCell('No projects found.', 'td'); td.colSpan = 6; td.style.textAlign = 'center'; td.style.color = '#999'; tr.appendChild(td); tbody.appendChild(tr); return; }
        projects.forEach(p => {
            const tr = document.createElement('tr');
            tr.appendChild(createCell(p.project_code)); tr.appendChild(createCell(p.project_name)); tr.appendChild(createCell(p.customer_name || '-'));
            const tdStatus = document.createElement('td'); tdStatus.appendChild(createPill(p.status, p.status === 'Active' ? 'green' : 'blue')); tr.appendChild(tdStatus);
            tr.appendChild(createCell(p.modules || '-'));
            const tdBtn = document.createElement('td'); const b = document.createElement('button'); b.className='btn btn-small'; b.textContent='Select'; b.addEventListener('click', () => selectProject(p.id)); tdBtn.appendChild(b); tr.appendChild(tdBtn);
            tbody.appendChild(tr);
        });
    } catch(err) { console.error(err); }
};

window.selectProject = function(id) { document.getElementById('globalProjectSelect').value = id; onGlobalProjectChange(); };

// Sessions and other list renderers keep same fetch logic but render safely
window.loadSessionsForGlobalProject = async function() {
    const tbody = document.getElementById('sessions-table-body'); if(!tbody) return;
    if(!globalProjectId) { clearChildren(tbody); const tr=document.createElement('tr'); const td=createCell('Please select a project from the header first.','td'); td.colSpan=6; td.style.textAlign='center'; td.style.color='#999'; tr.appendChild(td); tbody.appendChild(tr); return; }
    try {
        const response = await fetch(`/api/sessions?project_id=${globalProjectId}`);
        const sessions = await response.json(); clearChildren(tbody);
        if(sessions.length === 0) { const tr=document.createElement('tr'); const td=createCell('No sessions yet. Start a new session!','td'); td.colSpan=6; td.style.textAlign='center'; td.style.color='#999'; tr.appendChild(td); tbody.appendChild(tr); return; }
        sessions.forEach(s => {
            const tr = document.createElement('tr');
            tr.appendChild(createCell(s.session_name)); const td1=document.createElement('td'); td1.appendChild(createPill(s.module || '-', 'blue')); tr.appendChild(td1);
            tr.appendChild(createCell(s.process_name || '-'));
            const tdStat=document.createElement('td'); tdStat.appendChild(createPill(s.status, s.status === 'Completed' ? 'green' : 'orange')); tr.appendChild(tdStat);
            tr.appendChild(createCell('-'));
            const tdAction=document.createElement('td'); const b=document.createElement('button'); b.className='btn btn-small'; b.textContent='Open'; b.addEventListener('click', ()=>openSession(s.id)); tdAction.appendChild(b); tr.appendChild(tdAction);
            tbody.appendChild(tr);
        });
    } catch(err) { console.error(err); }
};

window.openSession = function(sessionId){ currentSessionId = sessionId; loadSessionDetail(sessionId); document.querySelectorAll('.view').forEach(v=>v.classList.remove('active')); document.getElementById('view-session-detail').classList.add('active'); };

// Questions rendering using safe DOM
window.loadQuestionsForSession = async function(sessionId) {
    try {
        const response = await fetch(`/api/questions?session_id=${sessionId}`);
        const questions = await response.json();
        const container = document.getElementById('questionsContainer'); clearChildren(container);
        if(!questions || questions.length===0) { const d=document.createElement('div'); d.style.textAlign='center'; d.style.color='#999'; d.style.padding='40px'; d.textContent='No questions yet.'; container.appendChild(d); return; }
        questions.forEach((q,i)=>{
            const card = document.createElement('div'); card.className='smart-card'; card.style.marginBottom='10px'; card.style.padding='15px'; card.style.background='#f8f9fa';
            const title = document.createElement('strong'); title.style.color='var(--primary)'; title.textContent=`Q${i+1}: ${q.question_text}`; card.appendChild(title);
            const div = document.createElement('div'); div.style.marginTop='10px'; div.style.padding='10px'; div.style.background='white'; div.style.borderRadius='8px'; div.style.borderLeft = `3px solid ${q.answer_text ? 'var(--primary)' : '#ccc'}`;
            if(q.answer_text) div.textContent = q.answer_text; else { const em=document.createElement('em'); em.style.color='#999'; em.textContent='Not answered yet'; div.appendChild(em);} card.appendChild(div); container.appendChild(card);
        });
    } catch(err) { console.error(err); }
};

// Safe sendDocChat implementation to avoid inserting unsanitized HTML
window.sendDocChat = function() {
    const input = document.getElementById('docChatInput'); if(!input) return; const text = input.value.trim(); if(!text) return;
    const area = document.getElementById('docChatArea');
    const userWrap = document.createElement('div'); userWrap.style.textAlign='right'; userWrap.style.marginBottom='10px';
    const userSpan = document.createElement('span'); userSpan.style.cssText = 'background:var(--primary);color:white;padding:8px 12px;border-radius:12px;display:inline-block;max-width:80%;'; userSpan.textContent = text; userWrap.appendChild(userSpan); area.appendChild(userWrap);
    input.value = '';
    area.scrollTop = area.scrollHeight;

    const typing = document.createElement('div'); typing.id = 'typing-indicator'; typing.style.marginBottom='10px';
    const typingSpan = document.createElement('span'); typingSpan.style.color = '#999'; typingSpan.textContent = '🤖 AI is typing...'; typing.appendChild(typingSpan);
    area.appendChild(typing);
    area.scrollTop = area.scrollHeight;

    // simulate API call - keep original mock behavior but sanitize incoming HTML
    setTimeout(()=>{
        typing.remove();
        const aiWrap = document.createElement('div'); aiWrap.style.marginBottom='10px';
        const aiSpan = document.createElement('div'); aiSpan.style.cssText='background:#f0f0f0;padding:12px;border-radius:12px;display:inline-block;max-width:80%;border-left:3px solid #8900B4;';
        const responseText = `AI: I'll help you with "${text}". This feature is coming soon!`;
        // set as text to avoid injecting HTML
        aiSpan.textContent = responseText;
        aiWrap.appendChild(aiSpan); area.appendChild(aiWrap);
        area.scrollTop = area.scrollHeight;
    }, 500);
};

// Requirements table rendering: use DOM, add keyboard support
window.renderRequirementsTable = function(requirements) {
    const tbody = document.getElementById('requirements-table-body'); if(!tbody) return; clearChildren(tbody);
    if(!requirements || requirements.length === 0) { const tr=document.createElement('tr'); const td=createCell('No requirements found.'); td.colSpan=7; td.style.textAlign='center'; td.style.color='#999'; tr.appendChild(td); tbody.appendChild(tr); return; }
    requirements.forEach(req => {
        const tr = document.createElement('tr'); tr.tabIndex=0; tr.setAttribute('role','button');
        tr.addEventListener('click', ()=>loadRequirementDetails(req.id));
        tr.addEventListener('keydown', (e)=>{ if(e.key==='Enter' || e.key===' ') loadRequirementDetails(req.id); });
        const tdCode = document.createElement('td'); const b=document.createElement('b'); b.textContent = req.code || '-'; tdCode.appendChild(b); tr.appendChild(tdCode);
        tr.appendChild(createCell(req.title || '-'));
        const tdModule = document.createElement('td'); tdModule.appendChild(createPill(req.module || '-', 'blue')); tr.appendChild(tdModule);
        tr.appendChild(createCell(req.complexity || '-'));
        const st = document.createElement('td'); st.appendChild(createPill(req.status || '-', req.status==='Ready' ? 'green' : 'orange')); tr.appendChild(st);
        const aiStat = document.createElement('td'); aiStat.style.color='#8900B4'; aiStat.style.fontSize='12px'; aiStat.textContent = req.ai_status === 'Full' ? '✦ Full' : '○ None'; tr.appendChild(aiStat);
        const tdAction = document.createElement('td'); tdAction.style.color='var(--primary)'; const edit = document.createElement('button'); edit.className='btn btn-small'; edit.textContent='Edit'; edit.addEventListener('click', (e)=>{ e.stopPropagation(); /* implement edit flow */ loadRequirementDetails(req.id); }); tdAction.appendChild(edit); tr.appendChild(tdAction);
        tbody.appendChild(tr);
    });
};

window.loadRequirements = async function() {
    try {
        let url = '/api/requirements'; if(globalProjectId) url += `?project_id=${globalProjectId}`;
        const response = await fetch(url); const requirements = await response.json(); renderRequirementsTable(requirements); updateRequirementsTabs(requirements);
    } catch(err) { console.error(err); }
};

window.updateRequirementsTabs = function(requirements) { const tabs = document.querySelectorAll('#view-requirements .tab-item'); if(tabs.length >= 4) tabs[0].textContent = `All Objects (${requirements.length})`; };

window.loadRequirementDetails = async function(id) { try { const res = await fetch(`/api/requirements/${id}`); const data = await res.json(); document.querySelector('#view-design .page-title') && (document.querySelector('#view-design .page-title').innerText = data.code); document.querySelector('#view-design .page-subtitle') && (document.querySelector('#view-design .page-subtitle').innerText = data.title); navTo('design'); } catch(e) { console.error(e); } };

// Keep saveRequirement similar but minimal client validation
window.saveRequirement = async function() {
    if(!globalProjectId) { alert('Please select a project first!'); return; }
    const code = document.getElementById('newCode').value.trim(); const title = document.getElementById('newTitle').value.trim();
    if(!code || !title) { alert('Fill all fields!'); return; }
    const data = { project_id: globalProjectId, code, title, module: document.getElementById('newModule').value, complexity: document.getElementById('newComplexity').value };
    try {
        const response = await fetch('/api/requirements', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) });
        if(response.ok) { closeModal('addModal'); loadRequirements(); showToast('Requirement saved!'); }
    } catch(err) { console.error(err); }
};

// A small set of passthrough server operations (projects/sessions/documents/testcases) use previously defined endpoints - keep original names for compatibility
window.saveNewProject = async function() {
    const data = { project_code: document.getElementById('projectCode').value, project_name: document.getElementById('projectName').value, customer_name: document.getElementById('customerName').value, modules: document.getElementById('projectModules').value, status: 'Planning' };
    if(!data.project_code || !data.project_name) { alert('Project Code and Name required!'); return; }
    try { const response = await fetch('/api/projects', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) }); if(response.ok) { closeModal('newProjectModal'); loadProjects(); loadGlobalProjectDropdown(); showToast('Project created!'); } } catch(err) { console.error(err); }
};

window.saveNewSession = async function() {
    const data = { project_id: globalProjectId, session_name: document.getElementById('sessionName').value, module: document.getElementById('sessionModule').value, process_name: document.getElementById('sessionProcessArea').value, status: 'Planned' };
    if(!data.session_name || !data.module) { alert('Session Name and Module required!'); return; }
    try { const response = await fetch('/api/sessions', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) }); if(response.ok) { closeModal('newSessionModal'); loadSessionsForGlobalProject(); showToast('Session created!'); } } catch(err) { console.error(err); }
};

// loadRequirementsForDocModal and loadDocumentsForTestModal - safe population
window.loadRequirementsForDocModal = async function() {
    try {
        const response = await fetch(`/api/requirements?project_id=${globalProjectId}`);
        const requirements = await response.json(); const select = document.getElementById('docRequirementSelect'); clearChildren(select); const defaultOpt=document.createElement('option'); defaultOpt.value=''; defaultOpt.textContent='-- Select Requirement --'; select.appendChild(defaultOpt); requirements.forEach(r=>{const opt=document.createElement('option'); opt.value=r.id; opt.textContent=`${r.code} - ${r.title}`; select.appendChild(opt);});
    } catch(err) { console.error(err); }
};

window.loadDocumentsForTestModal = async function() {
    try { const response = await fetch(`/api/documents?project_id=${globalProjectId}`); const documents = await response.json(); const select = document.getElementById('testDocumentSelect'); clearChildren(select); const defaultOpt=document.createElement('option'); defaultOpt.value=''; defaultOpt.textContent='-- Select FS/TS Document --'; select.appendChild(defaultOpt); documents.forEach(d=>{ const opt=document.createElement('option'); opt.value=d.id; opt.textContent=`${d.document_type}-${d.requirement_code}`; select.appendChild(opt); }); } catch(err){console.error(err);} };

// On DOM ready
document.addEventListener('DOMContentLoaded', () => {
    // wire header interactions
    const newProjectBtn = document.querySelector('button[onclick*="openNewProjectModal"]'); if(newProjectBtn) newProjectBtn.setAttribute('aria-haspopup','dialog');
    // initialize app
    initializeApp();
});
