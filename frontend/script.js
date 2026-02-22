const API_BASE = 'http://localhost:5000/api';

document.addEventListener('DOMContentLoaded', () => {
    initSystem();
    initSplashScreen();
    setupAuthEventListeners();
    setupEventListeners();

    // Home Navigation
    document.getElementById('logo-home').addEventListener('click', () => {
        navigateTo('dashboard');
    });

    // File Upload Listeners (Landing & Dashboard)
    const landingBtn = document.getElementById('landing-upload-btn');
    const landingInput = document.getElementById('landing-file-input');
    const dashboardBtn = document.getElementById('upload-btn');
    const dashboardUploadBtn = document.getElementById('upload-btn'); // Renamed for clarity
    const dashboardFileInput = document.getElementById('file-input'); // Renamed for clarity

    if (landingBtn && landingInput) {
        landingBtn.addEventListener('click', () => landingInput.click());
        landingInput.addEventListener('change', (e) => handleFileUpload(e, false)); // Fresh upload
    }
    if (dashboardUploadBtn && dashboardFileInput) {
        dashboardUploadBtn.addEventListener('click', () => dashboardFileInput.click());
        dashboardFileInput.addEventListener('change', (e) => handleFileUpload(e, true));
    }

    // Navigation Listeners
    document.getElementById('nav-dashboard').addEventListener('click', () => navigateTo('dashboard'));
    document.getElementById('nav-docs').addEventListener('click', () => navigateTo('docs'));
    document.getElementById('view-full-docs-btn').addEventListener('click', () => navigateTo('docs'));

    // Exit Session
});

async function resetSession(skipConfirm = false) {
    if (!skipConfirm && !confirm("Are you sure you want to exit? This will clear all session data.")) return false;

    try {
        const res = await fetch(`${API_BASE}/reset`, { method: 'POST' });
        if (res.ok) {
            // Clear UI state
            document.getElementById('total-tables').innerText = '0';
            document.getElementById('table-list').innerHTML = '';
            return true;
        }
    } catch (e) {
        console.error("Reset error:", e);
    }
    return false;
}

function initSplashScreen() {
    const splash = document.getElementById('video-splash');
    const video = document.getElementById('intro-video');
    const skipBtn = document.getElementById('skip-intro-btn');

    if (!splash || !video) return;

    // Start video playback
    video.play().catch(err => {
        console.warn("Video auto-play blocked or failed:", err);
        // If auto-play fails, we might stay dark, so let's just transition if it doesn't work
        // or wait for a user click. For now, we'll try to play.
    });

    const hideSplash = () => {
        splash.classList.add('fade-out');
        setTimeout(() => {
            splash.style.display = 'none';
        }, 800); // Match CSS transition time
    };

    video.onended = hideSplash;
    if (skipBtn) {
        skipBtn.onclick = hideSplash;
    }
}

async function handleFileUpload(event, append = false) {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    const statusEl = document.getElementById('system-status');
    statusEl.textContent = append ? "Appending Data..." : "Uploading & Processing...";
    statusEl.className = "status-pending";

    const formData = new FormData();
    formData.append('append', append);
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }

    try {
        const res = await fetch(`${API_BASE}/upload`, {
            method: 'POST',
            body: formData
        });

        let data;
        const contentType = res.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
            data = await res.json();
        } else {
            const text = await res.text();
            data = { message: text || "Server error with no details." };
        }

        if (res.ok) {
            statusEl.textContent = "Upload Success";
            statusEl.className = "status-ready";

            try {
                // Refresh Dashboard Data
                if (data.table_count !== undefined) {
                    document.getElementById('total-tables').innerText = data.table_count;
                }
                loadTables();
                updateDashboardMetrics();

                // Switch to App View
                switchView('app');

                // Ensure we are on the dashboard view
                if (typeof navigateTo === 'function') {
                    navigateTo('dashboard');
                } else {
                    document.getElementById('table-view').classList.add('hidden');
                    document.getElementById('dashboard-view').classList.remove('hidden');
                    document.querySelectorAll('#table-list li').forEach(li => li.classList.remove('active'));
                    currentTable = null;
                }
            } catch (uiError) {
                console.warn("Upload succeeded but UI update failed:", uiError);
            }

            if (data.message) alert(data.message);
        } else {
            statusEl.textContent = "Upload Failed";
            statusEl.className = "status-error";
            alert(data.message || "Failed to process files.");
        }
    } catch (e) {
        console.error(e);
        statusEl.textContent = "Upload Error";
        statusEl.className = "status-error";
        alert("An error occurred during upload.");
    } finally {
        // Reset input for next selection
        event.target.value = '';
    }
}

let currentTable = null;

function switchView(view) {
    const auth = document.getElementById('auth-view');
    const landing = document.getElementById('landing-view');
    const app = document.getElementById('app-container');
    const chatToggle = document.getElementById('open-chat-btn');
    const sidebarToggle = document.getElementById('open-sidebar-btn');

    // Hide everything first
    auth.classList.add('hidden');
    landing.classList.add('hidden');
    app.classList.add('hidden');
    chatToggle.classList.add('hidden');
    sidebarToggle.classList.add('hidden');

    if (view === 'auth') {
        auth.classList.remove('hidden');
    } else if (view === 'app') {
        app.classList.remove('hidden');
        chatToggle.classList.remove('hidden');
    } else if (view === 'landing') {
        landing.classList.remove('hidden');
    }
}

async function initSystem() {
    const statusEl = document.getElementById('system-status');
    statusEl.textContent = "Checking Session...";

    // Use onAuthStateChanged to handle initialization
    if (window.firebaseAuth && window.firebaseAuth.onAuthStateChanged) {
        window.firebaseAuth.onAuthStateChanged(window.firebaseAuth.auth, async (user) => {
            if (user) {
                console.log("User authenticated:", user.email);
                statusEl.textContent = "Initializing...";
                statusEl.className = "status-pending";

                try {
                    const res = await fetch(`${API_BASE}/dashboard`);
                    const data = await res.json();

                    if (res.ok && data.total_tables > 0) {
                        statusEl.textContent = "Welcome back, " + (user.displayName || user.email);
                        statusEl.className = "status-ready";
                        document.getElementById('total-tables').innerText = data.total_tables;
                        loadTables();
                        updateDashboardMetrics();
                        switchView('app');
                    } else {
                        statusEl.textContent = "Awaiting Multi-File Dataset";
                        statusEl.className = "status-pending";
                        switchView('landing');
                    }
                } catch (e) {
                    console.error(e);
                    statusEl.textContent = "Backend Offline";
                    statusEl.className = "status-error";
                    switchView('landing');
                }
            } else {
                console.log("No user logged in.");
                statusEl.textContent = "Awaiting Login";
                switchView('auth');
            }
        });
    } else {
        console.warn("Firebase Auth not initialized yet. Retrying in 500ms...");
        setTimeout(initSystem, 500);
    }
}

function setupAuthEventListeners() {
    // Auth Tab Toggles
    document.querySelectorAll('.auth-tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.auth-tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.auth-form').forEach(f => f.classList.remove('active'));

            e.target.classList.add('active');
            const authType = e.target.getAttribute('data-auth');
            document.getElementById(`${authType}-form`).classList.add('active');
        });
    });

    // Login Action
    const loginBtn = document.getElementById('login-btn');
    if (loginBtn) {
        loginBtn.addEventListener('click', async () => {
            const email = document.getElementById('login-email').value;
            const pass = document.getElementById('login-password').value;
            handleAuthAction('login', { email, pass });
        });
    }

    // Signup Action
    const signupBtn = document.getElementById('signup-btn');
    if (signupBtn) {
        signupBtn.addEventListener('click', async () => {
            const email = document.getElementById('signup-email').value;
            const pass = document.getElementById('signup-password').value;
            handleAuthAction('signup', { email, pass });
        });
    }

    // Google Login
    const googleBtn = document.getElementById('google-login-btn');
    if (googleBtn) {
        googleBtn.addEventListener('click', () => handleAuthAction('google'));
    }

    // Guest Login
    const guestBtn = document.getElementById('guest-login-btn');
    if (guestBtn) {
        guestBtn.addEventListener('click', () => {
            console.log("Guest login selected.");
            switchView('landing');
        });
    }

    // Modify Exit button to also Sign Out from Firebase
    const exitBtn = document.getElementById('exit-btn');
    if (exitBtn) {
        exitBtn.onclick = async () => {
            if (confirm("Sign out and clear current data session?")) {
                if (window.firebaseAuth && window.firebaseAuth.signOut) {
                    await window.firebaseAuth.signOut(window.firebaseAuth.auth);
                }
                const success = await resetSession(true); // skip second confirm
                if (success) {
                    switchView('auth');
                }
            }
        };
    }
}

async function handleAuthAction(type, creds = {}) {
    const errorEl = document.getElementById('auth-error');
    errorEl.classList.add('hidden');

    if (!window.firebaseAuth) return;
    const { auth, provider, signInWithPopup, signInWithEmailAndPassword, createUserWithEmailAndPassword } = window.firebaseAuth;

    try {
        if (type === 'google') {
            await signInWithPopup(auth, provider);
        } else if (type === 'login') {
            await signInWithEmailAndPassword(auth, creds.email, creds.pass);
        } else if (type === 'signup') {
            await createUserWithEmailAndPassword(auth, creds.email, creds.pass);
        }
        // onAuthStateChanged will handle the view switch
    } catch (error) {
        console.error("Auth Error:", error);
        errorEl.innerText = error.message;
        errorEl.classList.remove('hidden');
    }
}

async function loadTables() {
    try {
        const res = await fetch(`${API_BASE}/schema`);
        const schema = await res.json();
        const list = document.getElementById('table-list');
        list.innerHTML = '';

        if (schema.error) return;

        Object.keys(schema).forEach(tableName => {
            const li = document.createElement('li');
            li.innerText = tableName;
            li.onclick = () => loadTableDetails(tableName);
            list.appendChild(li);
        });

        // Compute total rows for dashboard
        let totalRows = 0;
        Object.values(schema).forEach(t => totalRows += t.row_count);
        document.getElementById('total-rows').innerText = totalRows.toLocaleString();

    } catch (e) {
        console.error("Error loading tables:", e);
    }
}

async function updateDashboardMetrics() {
    try {
        const res = await fetch(`${API_BASE}/dashboard`);
        const data = await res.json();

        if (data.error) return;

        document.getElementById('avg-trust').innerText = data.avg_trust_score;
        document.getElementById('total-tables').innerText = data.total_tables;
        document.getElementById('total-rows').innerText = data.total_rows.toLocaleString();

        // Dynamic Documentation
        if (data.project_info) {
            document.getElementById('doc-title').innerText = data.project_info.title || 'Project Overview';
            document.getElementById('doc-description').innerText = data.project_info.description || '';
            document.getElementById('dataset-context').innerText = data.project_info.context || data.project_info.dataset_context || '';

            // Value List
            const valueList = document.getElementById('business-value-list');
            valueList.innerHTML = '';
            const values = data.project_info.value || [];
            values.forEach(val => {
                const li = document.createElement('li');
                li.innerText = val;
                valueList.appendChild(li);
            });

            // Key Entities
            const entityContainer = document.getElementById('key-entities-tags');
            entityContainer.innerHTML = '';
            const entities = data.project_info.key_entities || [];
            entities.forEach(entity => {
                const span = document.createElement('span');
                span.className = 'entity-tag';
                span.innerText = entity;
                entityContainer.appendChild(span);
            });
        }
    } catch (e) {
        console.error("Error updating dashboard:", e);
    }
}

function navigateTo(view) {
    const dashboardView = document.getElementById('dashboard-view');
    const docView = document.getElementById('documentation-view');
    const tableView = document.getElementById('table-view');
    const navDashboard = document.getElementById('nav-dashboard');
    const navDocs = document.getElementById('nav-docs');

    // Hide all views
    dashboardView.classList.add('hidden');
    docView.classList.add('hidden');
    tableView.classList.add('hidden');

    // Deactivate all nav items
    navDashboard.classList.remove('active');
    navDocs.classList.remove('active');
    document.querySelectorAll('#table-list li').forEach(li => li.classList.remove('active'));

    if (view === 'dashboard') {
        dashboardView.classList.remove('hidden');
        navDashboard.classList.add('active');
        currentTable = null;
    } else if (view === 'docs') {
        docView.classList.remove('hidden');
        navDocs.classList.add('active');
        currentTable = null;
        loadFullDocumentation();
    }
}

async function loadFullDocumentation() {
    const summaryEl = document.getElementById('report-summary');
    const architectureEl = document.getElementById('report-architecture');
    const qualityEl = document.getElementById('report-quality');
    const titleEl = document.getElementById('report-title');
    const entityGrid = document.getElementById('report-entities');
    const utilityList = document.getElementById('report-utility-list');

    try {
        const res = await fetch(`${API_BASE}/full-docs`);
        const data = await res.json();

        if (data.error) throw new Error(data.error);

        titleEl.innerText = data.title || "Dataset Documentation Report";
        summaryEl.innerText = data.executive_summary || "No summary available.";
        architectureEl.innerText = data.architecture_overview || "No architecture details available.";
        qualityEl.innerText = data.data_quality_narrative || "No quality assessment available.";

        // Render Entities
        entityGrid.innerHTML = '';
        (data.key_entities || []).forEach(entity => {
            const card = document.createElement('div');
            card.className = 'entity-detail-card';
            card.innerHTML = `<strong>${entity.name}</strong><span>${entity.description}</span>`;
            entityGrid.appendChild(card);
        });

        // Render Utility
        utilityList.innerHTML = '';
        (data.business_utility || []).forEach(item => {
            const li = document.createElement('li');
            li.innerText = item;
            utilityList.appendChild(li);
        });

    } catch (e) {
        console.error("Full Docs Error:", e);
        summaryEl.innerText = "Failed to load documentation. Please try again later.";
    }
}

async function loadTableDetails(tableName) {
    currentTable = tableName;

    // Update UI selection
    const tableItems = document.querySelectorAll('#table-list li');
    tableItems.forEach(li => li.classList.remove('active'));

    // Find the item that matches the tableName
    tableItems.forEach(li => {
        if (li.innerText === tableName) li.classList.add('active');
    });

    // Switch View
    document.getElementById('dashboard-view').classList.add('hidden');
    document.getElementById('table-view').classList.remove('hidden');

    document.getElementById('current-table-name').innerText = tableName;

    // Reset Data
    document.getElementById('schema-body').innerHTML = '<tr><td colspan="5">Loading...</td></tr>';
    document.getElementById('id-health-val').innerText = '-';
    document.getElementById('fk-integrity-val').innerText = '-';
    document.getElementById('completeness-val').innerText = '-';
    document.getElementById('numeric-sanity-val').innerText = '-';
    document.getElementById('freshness-val').innerText = '-';
    document.getElementById('trust-score-val').innerText = '-';

    // Fetch Schema actions
    fetchTableSchema(tableName);
    fetchTableQuality(tableName);
}

async function fetchTableSchema(tableName) {
    const res = await fetch(`${API_BASE}/schema`);
    const allSchema = await res.json();
    const tableSchema = allSchema[tableName];

    const tbody = document.getElementById('schema-body');
    tbody.innerHTML = '';

    tableSchema.columns.forEach(col => {
        const tr = document.createElement('tr');
        const nullPct = ((col.null_count / tableSchema.row_count) * 100).toFixed(2);
        const uniquePct = ((col.unique_count / tableSchema.row_count) * 100).toFixed(2);

        tr.innerHTML = `
            <td>${col.name} ${tableSchema.potential_keys.includes(col.name) ? '🔑' : ''}</td>
            <td>${col.type}</td>
            <td>-</td> 
            <td>${nullPct}%</td>
            <td>${uniquePct}%</td>
        `;
        tbody.appendChild(tr);
    });
}

async function fetchTableQuality(tableName) {
    const res = await fetch(`${API_BASE}/quality/${tableName}`);
    const metrics = await res.json();

    if (metrics.error) return;

    document.getElementById('id-health-val').innerText = metrics.sub_scores.identifier_health + '/100';
    document.getElementById('fk-integrity-val').innerText = metrics.sub_scores.fk_integrity + '/100';
    document.getElementById('completeness-val').innerText = metrics.completeness + '%';
    document.getElementById('numeric-sanity-val').innerText = metrics.sub_scores.numeric_sanity + '/100';
    document.getElementById('freshness-val').innerText = metrics.freshness + '/100';

    const scoreEl = document.getElementById('trust-score-val');
    scoreEl.innerText = metrics.trust_score;

    // Color code trust score
    const score = metrics.trust_score;
    const badge = document.getElementById('trust-display');
    if (score >= 90) {
        badge.style.backgroundColor = '#dcfce7';
        badge.style.color = '#166534';
        badge.style.borderColor = '#bbf7d0';
    } else if (score >= 70) {
        badge.style.backgroundColor = '#fef9c3';
        badge.style.color = '#854d0e';
        badge.style.borderColor = '#fde047';
    } else {
        badge.style.backgroundColor = '#fee2e2';
        badge.style.color = '#991b1b';
        badge.style.borderColor = '#fecaca';
    }

    const issuesList = document.getElementById('issues-list');
    issuesList.innerHTML = '';
    if (metrics.issues && metrics.issues.length > 0) {
        metrics.issues.forEach(issue => {
            const li = document.createElement('li');
            li.style.display = 'flex';
            li.style.justifyContent = 'space-between';
            li.style.alignItems = 'center';
            li.style.marginBottom = '8px';

            const span = document.createElement('span');
            span.innerText = issue;
            li.appendChild(span);

            // If it's an outlier issue, add a "Why?" button
            if (issue.toLowerCase().includes('outlier')) {
                const whyBtn = document.createElement('button');
                whyBtn.className = 'secondary-btn small-btn';
                whyBtn.innerText = 'Why?';
                whyBtn.style.padding = '2px 8px';
                whyBtn.style.fontSize = '0.75rem';
                whyBtn.onclick = () => showOutlierReasoning(tableName, issue);
                li.appendChild(whyBtn);
            }

            issuesList.appendChild(li);
        });
    } else {
        issuesList.innerHTML = '<li>No major issues detected.</li>';
    }
}

async function showOutlierReasoning(tableName, issue) {
    // Extract column name from issue string "High outlier rate in <col> (...)"
    const match = issue.match(/in ([\w_]+)/);
    if (!match) return;
    const colName = match[1];

    alert(`Analyzing logical context for ${colName} outliers...`);

    try {
        const res = await fetch(`${API_BASE}/outlier-reasoning`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                table_name: tableName,
                column_name: colName,
                row_index: 0 // Just sample the first row for now as context
            })
        });
        const data = await res.json();
        alert(`AI Reasoning: ${data.reason || "Unable to determine logical context."}`);
    } catch (e) {
        alert("Failed to connect to reasoning core.");
    }
}



function setupEventListeners() {
    // Tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

            e.target.classList.add('active');
            const tabId = e.target.getAttribute('data-tab');
            document.getElementById(`tab-${tabId}`).classList.add('active');
        });
    });

    // AI Button Removal - no longer needed

    // Chat
    document.getElementById('send-btn').addEventListener('click', sendMessage);
    document.getElementById('chat-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    // Sidebar Toggles
    const toggleSidebarBtn = document.getElementById('toggle-sidebar-btn');
    const openSidebarBtn = document.getElementById('open-sidebar-btn');
    const sidebar = document.getElementById('sidebar-panel');

    if (toggleSidebarBtn) {
        toggleSidebarBtn.addEventListener('click', () => {
            sidebar.classList.add('collapsed');
            openSidebarBtn.classList.remove('hidden');
        });
    }

    if (openSidebarBtn) {
        openSidebarBtn.addEventListener('click', () => {
            sidebar.classList.remove('collapsed');
            openSidebarBtn.classList.add('hidden');
        });
    }

    // Chat Toggles
    const miniChatBtn = document.getElementById('minimize-chat-btn');
    const openChatBtn = document.getElementById('open-chat-btn');
    const chatPanel = document.getElementById('chat-panel');

    if (miniChatBtn) {
        miniChatBtn.addEventListener('click', () => {
            chatPanel.classList.add('hidden');
            openChatBtn.classList.remove('hidden');
        });
    }

    if (openChatBtn) {
        openChatBtn.addEventListener('click', () => {
            chatPanel.classList.remove('hidden');
            openChatBtn.classList.add('hidden');
            // Auto scroll to bottom
            const container = document.getElementById('chat-messages');
            container.scrollTop = container.scrollHeight;
        });
    }

    // AI Analysis Trigger
    const genAnalysisBtn = document.getElementById('gen-analysis-btn');
    if (genAnalysisBtn) {
        genAnalysisBtn.addEventListener('click', generateAIAnalysis);
    }
}

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const text = input.value.trim();
    if (!text) return;

    addMessage(text, 'user');
    input.value = '';

    const typingId = showTypingIndicator();

    try {
        const res = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: text })
        });
        const data = await res.json();
        hideTypingIndicator(typingId);
        addMessage(data.answer, 'bot');
    } catch (e) {
        hideTypingIndicator(typingId);
        addMessage("Sorry, I couldn't reach the server.", 'bot');
    }
}

function showTypingIndicator() {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    const id = 'typing-' + Date.now();
    div.id = id;
    div.className = 'typing-loader';
    div.innerHTML = `
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return id;
}

function hideTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function addMessage(text, sender) {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = `msg ${sender}`;
    div.innerText = text;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}
async function generateAIAnalysis() {
    if (!currentTable) return;

    const btn = document.getElementById('gen-analysis-btn');
    const content = document.getElementById('ai-summary-content');

    btn.disabled = true;
    btn.innerText = "Generating...";
    content.innerHTML = '<div class="loading-spinner">Analyzing data logic...</div>';

    try {
        const res = await fetch(`${API_BASE}/summary/${currentTable}`);
        const data = await res.json();

        if (data.error) throw new Error(data.error);

        content.innerHTML = `
            <div class="ai-summary-result">
                <div class="ai-classification badge">${data.classification || 'General'}</div>
                <p class="ai-desc">**Summary**: ${data.summary}</p>
                
                <div class="ai-detail-item">
                    <strong>Business Impact</strong>
                    <p>${data.impact}</p>
                </div>
                
                <div class="ai-detail-item">
                    <strong>Logical Risks</strong>
                    <p>${data.risks}</p>
                </div>

                <div class="ai-detail-item">
                    <strong>Key Columns</strong>
                    <div class="entity-tags">
                        ${(data.important_columns || []).map(col => `<span class="entity-tag">${col}</span>`).join('')}
                    </div>
                </div>
            </div>
        `;

    } catch (e) {
        console.error("AI Analysis Error:", e);
        content.innerHTML = `<p class="error">**Connectivity Issue**: ${e.message}</p>`;
    } finally {
        btn.disabled = false;
        btn.innerText = "Generate Analysis";
    }
}
