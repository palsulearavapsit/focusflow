/**
 * FocusFlow Study Session Logic
 * Handles session timer, state management, and API integration
 */

// Session State
let sessionState = {
    active: false,
    paused: false,
    startTime: null,
    duration: 0, // in seconds
    timerInterval: null,
    technique: 'pomodoro',
    studyMode: 'screen',
    cameraEnabled: false,
    distractions: 0,
    tabSwitches: 0,
    mouseInactiveTime: 0,
    keyboardInactiveTime: 0,
    cameraAbsenceTime: 0,
    faceAbsenceTime: 0,
    idleTime: 0,
    currentState: 'focused'
};

// DOM Elements
const elements = {
    setup: document.getElementById('sessionSetup'),
    active: document.getElementById('activeSession'),
    summary: document.getElementById('sessionSummary'),
    timer: document.getElementById('timerDisplay'),
    techniqueSelect: document.getElementById('techniqueSelect'),
    modeSelect: document.getElementById('modeSelect'),
    cameraToggle: document.getElementById('cameraToggle'),
    startBtn: document.getElementById('startSessionBtn'),
    endBtn: document.getElementById('endSessionBtn'),
    pauseBtn: document.getElementById('pauseSessionBtn'),
    distractionCount: document.getElementById('distractionCount'),
    tabSwitchCount: document.getElementById('tabSwitchCount'),
    currentState: document.getElementById('currentState'),
    idleTime: document.getElementById('idleTime'),
    sessionInfo: document.getElementById('sessionInfo'),
    userGreeting: document.getElementById('userGreeting'),
    // Summary elements
    finalFocusScore: document.getElementById('finalFocusScore'),
    summaryDuration: document.getElementById('summaryDuration'),
    summaryDistractions: document.getElementById('summaryDistractions'),
    summaryState: document.getElementById('summaryState'),
    recommendationAlert: document.getElementById('recommendationAlert'),
    recommendationText: document.getElementById('recommendationText')
};

// Study Techniques Configuration (in seconds)
const TECHNIQUES = {
    'pomodoro': { name: 'Pomodoro', study: 25 * 60, break: 5 * 60 },
    '52-17': { name: '52-17 Technique', study: 52 * 60, break: 17 * 60 },
    'study-sprint': { name: 'Study Sprint', study: 15 * 60, break: 5 * 60 },
    'flowtime': { name: 'Flowtime', study: null, break: null } // Open-ended
};

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    // Check auth
    if (!await protectPage('student')) return;

    // Display user info
    const user = getUser();
    if (user && elements.userGreeting) {
        elements.userGreeting.innerText = `Welcome back, ${user.username}`;
    }

    // Check for active session recovery
    checkActiveSession();

    // Load available classrooms
    loadStudentClassrooms();

    // Initialize modules
    if (typeof initializeDistractionDetection === 'function') {
        initializeDistractionDetection();
    }

    // Initialize Study Tools
    initializeStudyTools();

    // Check URL Params for Shortcuts
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('mode') === 'group') {
        const modeSelect = document.getElementById('modeSelect');
        if (modeSelect) modeSelect.value = 'group';
    }
});

// --- Study Tools Logic ---

function initializeStudyTools() {
    // YouTube
    const analyzeBtn = document.getElementById('analyzeEmbedBtn');
    if (analyzeBtn) {
        // Remove old listener to prevent duplicates if function called multiple times
        analyzeBtn.removeEventListener('click', analyzeYouTubeVideo);
        analyzeBtn.addEventListener('click', analyzeYouTubeVideo);
    }

    // PDF
    const pdfInput = document.getElementById('pdfUploadInput');
    if (pdfInput) {
        pdfInput.removeEventListener('change', handlePDFUpload);
        pdfInput.addEventListener('change', handlePDFUpload);
    } else {
        // console.warn("PDF input not found in DOM");
    }

    // Load Archive on Init
    try {
        renderNotesArchive();
    } catch (e) {
        // console.error("Error rendering archive:", e);
    }
}

async function analyzeYouTubeVideo() {
    const input = document.getElementById('youtubeLinkInput');
    const resultDiv = document.getElementById('youtubeAnalysisResult');
    const container = document.getElementById('videoContainer');
    const iframe = document.getElementById('youtubeEmbedFrame');
    const btn = document.getElementById('analyzeEmbedBtn');
    const url = input.value.trim();

    if (!url) {
        resultDiv.className = 'alert alert-warning mb-2 py-2 small';
        resultDiv.innerHTML = '⚠️ Please paste a YouTube link first.';
        resultDiv.classList.remove('d-none');
        return;
    }

    // --- Loading State ---
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Checking...';
    resultDiv.className = 'alert alert-secondary mb-2 py-2 small d-flex align-items-center gap-2';
    resultDiv.innerHTML = `
        <span class="spinner-border spinner-border-sm text-light" role="status"></span>
        <span>🤖 <strong>Gemini AI</strong> is verifying if this video is study-related...</span>
    `;
    resultDiv.classList.remove('d-none');
    container.classList.add('d-none');
    iframe.src = '';

    try {
        const response = await authenticatedFetch(`${API_URL}/api/tools/analyze_youtube`, {
            method: 'POST',
            body: JSON.stringify({ url })
        });

        if (!response.ok) throw new Error(`Server error: ${response.status}`);

        const data = await response.json();
        const confPct = Math.round((data.confidence || 0) * 100);
        const videoId = data.video_id || extractVideoId(url);

        if (data.is_study_related) {
            // ✅ STUDY CONTENT
            resultDiv.className = 'alert mb-2 py-2 small';
            resultDiv.style.background = 'rgba(25,135,84,0.15)';
            resultDiv.style.border = '1px solid rgba(25,135,84,0.5)';
            resultDiv.style.color = '#d1e7dd';
            resultDiv.innerHTML = `
                <div class="d-flex justify-content-between align-items-start mb-1">
                    <strong>✅ Study Content Approved</strong>
                    <span class="badge" style="background:rgba(25,135,84,0.5);font-size:0.7rem;">${confPct}% confident</span>
                </div>
                <div style="font-size:0.7rem;opacity:0.85;margin-bottom:6px;font-style:italic;">
                    📺 ${escapeHtml(data.title)}
                </div>
                <div class="progress mb-2" style="height:4px;background:rgba(255,255,255,0.1);">
                    <div class="progress-bar bg-success" style="width:${confPct}%;"></div>
                </div>
                <div style="font-size:0.7rem;opacity:0.8;">🧠 ${escapeHtml(data.reason)}</div>
            `;

            if (videoId) {
                iframe.src = `https://www.youtube.com/embed/${videoId}?autoplay=1`;
                container.classList.remove('d-none');
            } else {
                showAlert('Could not extract video ID for embedding.', 'warning');
            }

        } else {
            // ❌ DISTRACTION CONTENT
            resultDiv.className = 'alert mb-2 py-2 small';
            resultDiv.style.background = 'rgba(220,53,69,0.15)';
            resultDiv.style.border = '1px solid rgba(220,53,69,0.5)';
            resultDiv.style.color = '#f8d7da';

            // Countdown before allowing "Watch Anyway"
            const COUNTDOWN = 5;
            let remaining = COUNTDOWN;

            const renderDistraction = (secs) => {
                const btnHtml = secs > 0
                    ? `<button class="btn btn-sm mt-2" disabled
                           style="background:rgba(220,53,69,0.3);color:#f8d7da;border:1px solid rgba(220,53,69,0.5);font-size:0.7rem;">
                           ⛔ Watch Anyway (${secs}s)
                       </button>`
                    : `<button class="btn btn-sm mt-2" onclick="forceEmbed('${escapeHtml(url)}')"
                           style="background:rgba(220,53,69,0.3);color:#f8d7da;border:1px solid rgba(220,53,69,0.5);font-size:0.7rem;">
                           ⚠️ Watch Anyway (Not Recommended)
                       </button>`;

                resultDiv.innerHTML = `
                    <div class="d-flex justify-content-between align-items-start mb-1">
                        <strong>⚠️ Distraction Detected</strong>
                        <span class="badge" style="background:rgba(220,53,69,0.5);font-size:0.7rem;">${confPct}% confident</span>
                    </div>
                    <div style="font-size:0.7rem;opacity:0.85;margin-bottom:6px;font-style:italic;">
                        📺 ${escapeHtml(data.title)}
                    </div>
                    <div class="progress mb-2" style="height:4px;background:rgba(255,255,255,0.1);">
                        <div class="progress-bar bg-danger" style="width:${confPct}%;"></div>
                    </div>
                    <div style="font-size:0.7rem;opacity:0.8;">🧠 ${escapeHtml(data.reason)}</div>
                    ${btnHtml}
                `;
            };

            renderDistraction(remaining);

            const interval = setInterval(() => {
                remaining--;
                renderDistraction(remaining);
                if (remaining <= 0) clearInterval(interval);
            }, 1000);
        }

    } catch (e) {
        console.error('[YouTube Analyze]', e);
        resultDiv.className = 'alert alert-warning mb-2 py-2 small';
        resultDiv.style.background = '';
        resultDiv.style.border = '';
        resultDiv.style.color = '';
        resultDiv.innerHTML = `⚠️ Could not analyze video. Please check the link and try again.<br><small class="opacity-75">${e.message}</small>`;
    } finally {
        btn.disabled = false;
        btn.innerHTML = 'Load';
    }
}

function extractVideoId(url) {
    const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=)([^#&?]*).*/;
    const match = url.match(regExp);
    return (match && match[2].length === 11) ? match[2] : null;
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#039;');
}

// Global scope for the "Watch Anyway" button (called from inline HTML)
window.forceEmbed = function (url) {
    const container = document.getElementById('videoContainer');
    const iframe = document.getElementById('youtubeEmbedFrame');
    const videoId = extractVideoId(url);
    if (videoId) {
        iframe.src = `https://www.youtube.com/embed/${videoId}?autoplay=1`;
        container.classList.remove('d-none');
    }
};

// --- PDF Logic (Session-Scoped) ---

/**
 * In-memory list of PDFs for the CURRENT session only.
 * Each entry: { name: string, url: string (blob URL) }
 * Cleared (and blob URLs revoked) whenever a new session starts.
 */
let sessionPDFs = [];
let activePDFIndex = -1;

/** Clear all session PDFs, revoke blob URLs, reset the viewer */
function clearSessionPDFs() {
    // Revoke all blob URLs so they can't be accessed after session ends
    sessionPDFs.forEach(pdf => {
        try { URL.revokeObjectURL(pdf.url); } catch (e) {}
    });
    sessionPDFs = [];
    activePDFIndex = -1;

    // Reset viewer
    const viewer = document.getElementById('pdfFrame');
    const placeholder = document.getElementById('pdfPlaceholder');
    if (viewer) { viewer.src = ''; viewer.classList.add('d-none'); }
    if (placeholder) placeholder.classList.remove('d-none');

    // Clear tabs
    renderPDFTabs();

    // Also clear the old localStorage archive so old names don't linger
    localStorage.removeItem('study_notes_archive');
}

function handlePDFUpload(e) {
    const file = e.target.files[0];
    // Reset input so the same file can be uploaded again if needed
    e.target.value = '';

    if (!file || file.type !== 'application/pdf') {
        alert('Please select a valid PDF file.');
        return;
    }

    // Create blob URL for this session
    const objUrl = URL.createObjectURL(file);

    // Avoid adding duplicate names within the same session
    const exists = sessionPDFs.findIndex(p => p.name === file.name);
    if (exists !== -1) {
        // Just switch to the existing one
        switchToPDF(exists);
        return;
    }

    sessionPDFs.push({ name: file.name, url: objUrl });
    activePDFIndex = sessionPDFs.length - 1;

    renderPDFTabs();
    displayPDF(objUrl, activePDFIndex);
}

function displayPDF(url, index) {
    const viewer = document.getElementById('pdfFrame');
    const placeholder = document.getElementById('pdfPlaceholder');

    if (placeholder) placeholder.classList.add('d-none');
    viewer.src = url;
    viewer.classList.remove('d-none');

    activePDFIndex = index;
    renderPDFTabs(); // re-render to update active state
}

function switchToPDF(index) {
    if (index < 0 || index >= sessionPDFs.length) return;
    displayPDF(sessionPDFs[index].url, index);
}

function renderPDFTabs() {
    const container = document.getElementById('pdfTabsContainer');
    if (!container) return;

    if (sessionPDFs.length === 0) {
        container.innerHTML = '';
        container.classList.add('d-none');
        return;
    }

    container.classList.remove('d-none');
    container.innerHTML = '';

    sessionPDFs.forEach((pdf, i) => {
        const tab = document.createElement('button');
        tab.className = 'pdf-tab btn btn-sm' + (i === activePDFIndex ? ' active' : '');
        tab.title = pdf.name;
        tab.innerHTML = `
            <span class="pdf-tab-name">${escapeHtml(truncateName(pdf.name, 18))}</span>
            <span class="pdf-tab-close" data-index="${i}" title="Remove">×</span>
        `;
        tab.addEventListener('click', (e) => {
            // If the × was clicked, remove instead of switching
            if (e.target.dataset.index !== undefined) {
                e.stopPropagation();
                removePDF(parseInt(e.target.dataset.index));
            } else {
                switchToPDF(i);
            }
        });
        container.appendChild(tab);
    });
}

function removePDF(index) {
    if (index < 0 || index >= sessionPDFs.length) return;
    try { URL.revokeObjectURL(sessionPDFs[index].url); } catch (e) {}
    sessionPDFs.splice(index, 1);

    if (sessionPDFs.length === 0) {
        activePDFIndex = -1;
        const viewer = document.getElementById('pdfFrame');
        const placeholder = document.getElementById('pdfPlaceholder');
        if (viewer) { viewer.src = ''; viewer.classList.add('d-none'); }
        if (placeholder) placeholder.classList.remove('d-none');
    } else {
        // Stay on nearest tab
        activePDFIndex = Math.min(index, sessionPDFs.length - 1);
        displayPDF(sessionPDFs[activePDFIndex].url, activePDFIndex);
    }
    renderPDFTabs();
}

function truncateName(name, maxLen) {
    // Remove .pdf extension for display, then truncate
    const base = name.replace(/\.pdf$/i, '');
    return base.length > maxLen ? base.substring(0, maxLen) + '…' : base;
}

// Keep renderNotesArchive as a no-op stub so initializeStudyTools doesn't crash
function renderNotesArchive() {}

async function loadStudentClassrooms() {
    try {
        const response = await authenticatedFetch(`${API_URL}/api/classrooms/student/list`);
        if (!response.ok) return; // Silent fail if not found or err

        const classrooms = await response.json();
        const select = document.getElementById('classroomSelect');

        if (classrooms.length > 0 && select) {
            classrooms.forEach(cls => {
                const option = document.createElement('option');
                option.value = cls.id;
                option.text = cls.name;
                select.appendChild(option);
            });
        }
    } catch (e) {
        console.warn("Could not load classrooms for dropdown", e);
    }
}

// Event Listeners
if (elements.startBtn) elements.startBtn.addEventListener('click', startSession);
if (elements.endBtn) elements.endBtn.addEventListener('click', endSession);
if (elements.pauseBtn) elements.pauseBtn.addEventListener('click', togglePause);

// Start Session
async function startSession() {
    try {
        const technique = elements.techniqueSelect.value;
        const studyMode = elements.modeSelect.value;
        const cameraEnabled = elements.cameraToggle.checked;
        const classroomId = document.getElementById('classroomSelect') ? document.getElementById('classroomSelect').value : null;

        // Call API to start session
        const response = await authenticatedFetch(`${API_URL}/api/sessions/start`, {
            method: 'POST',
            body: JSON.stringify({
                technique,
                study_mode: studyMode,
                camera_enabled: cameraEnabled,
                classroom_id: classroomId ? parseInt(classroomId) : null
            })
        });

        if (!response.ok) throw new Error('Failed to start session');

        // Clear PDFs from any previous session BEFORE starting a fresh one
        clearSessionPDFs();

        // Update local state
        sessionState = {
            ...sessionState,
            active: true,
            startTime: Date.now(),
            technique,
            studyMode,
            cameraEnabled,
            duration: 0
        };

        // Initialize camera if enabled
        if (cameraEnabled && typeof startCamera === 'function') {
            const cameraStarted = await startCamera();
            if (!cameraStarted) {
                sessionState.cameraEnabled = false;
                showAlert('Camera access failed. Continuing without camera.', 'warning');
            } else {
                // Start Visual Detection Loop (Overlay)
                if (typeof startFaceDetectionLoop === 'function') {
                    const videoEl = document.getElementById('cameraPreview');
                    startFaceDetectionLoop(videoEl);
                }
            }
        }

        // Start monitoring
        startMonitoring();

        // Update UI
        updateUIForSessionStart();

        // Enforce Fullscreen for Screen Mode
        if (studyMode === 'screen' && document.documentElement.requestFullscreen) {
            try {
                // Must be triggered by user activation, which the click on Start button provides
                await document.documentElement.requestFullscreen();
            } catch (fsErr) {
                console.warn("Fullscreen request failed", fsErr);
                showAlert("Please enable fullscreen manually for strict mode.", "warning");
            }
        }

        // Start Timer
        startTimer();

    } catch (error) {
        console.error('Start session error:', error);
        showAlert('Could not start session. Please try again.', 'error');
    }
}

// Timer Logic
function startTimer() {
    // Clear existing timer
    if (sessionState.timerInterval) clearInterval(sessionState.timerInterval);

    const config = TECHNIQUES[sessionState.technique];
    let remainingTime = config.study; // Can be null for flowtime

    // Adjust for resumed sessions
    if (remainingTime !== null && sessionState.duration > 0) {
        remainingTime -= sessionState.duration;
    }

    sessionState.timerInterval = setInterval(() => {
        if (sessionState.paused) return;

        sessionState.duration++;

        // Update display
        if (remainingTime !== null) {
            remainingTime--;
            updateTimerDisplay(remainingTime);

            if (remainingTime <= 0) {
                // Time's up
                clearInterval(sessionState.timerInterval);
                playNotificationSound();
                showAlert("Study session complete! Time for a break.", "success");
                // Allow user to continue or end manually
            }
        } else {
            // Flowtime (count up)
            updateTimerDisplay(sessionState.duration);
        }

        // Update stats every second
        updateLiveStats();

    }, 1000);

    // Initial display update
    if (remainingTime !== null) {
        updateTimerDisplay(remainingTime);
    } else {
        updateTimerDisplay(0);
    }
}

function updateTimerDisplay(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    elements.timer.innerText = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

// Monitoring Loop
function startMonitoring() {
    // Start distraction detection
    if (typeof startDistractionTracking === 'function') {
        startDistractionTracking(sessionState.studyMode);
    }

    // Periodically update session state from modules
    setInterval(async () => {
        if (!sessionState.active || sessionState.paused) return;

        if (typeof getDistractionMetrics === 'function') {
            const metrics = getDistractionMetrics();
            sessionState.distractions = metrics.distractionCount;
            sessionState.tabSwitches = metrics.tabSwitches;

            // Restore idle metrics
            sessionState.mouseInactiveTime = metrics.mouseInactiveTime;
            sessionState.keyboardInactiveTime = metrics.keyboardInactiveTime;
            sessionState.idleTime = metrics.mouseInactiveTime / 1000;

            // Sync current state
            sessionState.currentState = metrics.currentState;
        }

        // Peer Room Logic (Every 5 seconds)
        if (sessionState.studyMode === 'group' && sessionState.duration % 5 === 0) {
            try {
                // Mock participants for now (single user room)
                const response = await authenticatedFetch(`${API_URL}/api/ml/study-room-moderator`, {
                    method: 'POST',
                    body: JSON.stringify({
                        total_participants: 1,
                        current_participant_focus_score: 80, // Mock
                        average_room_focus_score: 75, // Mock
                        mic_status: "OFF",
                        camera_status: sessionState.cameraEnabled ? "ON" : "OFF",
                        fullscreen_status: document.fullscreenElement ? "ACTIVE" : "INACTIVE",
                        distraction_events_last_5_min: 0,
                        lock_mode_violations: violationCount,
                        session_time_remaining_minutes: 25 - (sessionState.duration / 60)
                    })
                });

                if (response.ok) {
                    const data = await response.json();
                    if (data.room_message) {
                        showAlert(`📢 Room Message: ${data.room_message}`, 'info');
                    }
                    if (data.private_message) {
                        showAlert(`🔒 Private Notice: ${data.private_message}`, 'warning');
                    }
                }
            } catch (e) {
                console.warn("Moderator sync failed", e);
            }
        }
    }, 1000);
}

// End Session
async function endSession() {
    if (!confirm('Are you sure you want to end this session?')) return;

    try {
        clearInterval(sessionState.timerInterval);

        // Stop modules
        if (typeof stopFaceDetectionLoop === 'function') stopFaceDetectionLoop();
        if (typeof stopCamera === 'function') stopCamera();
        if (typeof stopDistractionTracking === 'function') stopDistractionTracking();

        const payload = {
            duration: sessionState.duration,
            distractions: sessionState.distractions,
            mouse_inactive_time: Math.round(sessionState.mouseInactiveTime / 1000),
            keyboard_inactive_time: Math.round(sessionState.keyboardInactiveTime / 1000),
            tab_switches: sessionState.tabSwitches,
            camera_absence_time: Math.round(sessionState.cameraAbsenceTime / 1000),
            // Phase-2 placeholders
            face_absence_time: 0,
            dominant_emotion: "UNKNOWN",
            emotion_confidence: 0.0,
            user_state: sessionState.currentState || 'focused'
        };

        // Call API
        const response = await authenticatedFetch(`${API_URL}/api/sessions/end`, {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            let errorDetail = 'Failed to end session';
            try {
                const errData = await response.json();
                errorDetail = errData.detail || errorDetail;

                // Handle "No active session" specifically (mostly due to server restart)
                if (response.status === 400 && errorDetail.includes("active session")) {
                    alert("Your session timed out or server restarted. Redirecting to dashboard.");
                    window.location.href = "student_dashboard.html";
                    return;
                }
            } catch (e) {
                // Ignore JSON parse error
            }
            throw new Error(errorDetail);
        }

        const summary = await response.json();

        // Show Summary
        showSummary(summary);

    } catch (error) {
        console.error('End session error:', error);
        showAlert(error.message || 'Error saving session. Please check your connection.', 'error');
    }
}

// Toggle Pause
function togglePause() {
    sessionState.paused = !sessionState.paused;
    elements.pauseBtn.innerText = sessionState.paused ? 'Resume' : 'Pause';
    elements.timer.style.opacity = sessionState.paused ? '0.5' : '1';
}

// UI Updates
function updateUIForSessionStart() {
    elements.setup.classList.add('hidden');
    elements.active.classList.remove('hidden');

    const techName = TECHNIQUES[sessionState.technique].name;
    const modeName = sessionState.studyMode === 'screen' ? 'Screen Mode' : 'Book Mode';
    elements.sessionInfo.innerText = `${techName} • ${modeName}`;

    if (sessionState.cameraEnabled) {
        document.getElementById('cameraContainer').classList.remove('hidden');
    }
}

function updateLiveStats() {
    elements.distractionCount.innerText = sessionState.distractions;
    elements.tabSwitchCount.innerText = sessionState.tabSwitches;
    elements.currentState.innerText = capitalize(sessionState.currentState);

    // Format idle time
    const idleSecs = Math.round(sessionState.idleTime);
    if (idleSecs < 60) {
        elements.idleTime.innerText = `${idleSecs}s`;
    } else {
        elements.idleTime.innerText = `${Math.floor(idleSecs / 60)}m`;
    }
}

function showSummary(summary) {
    elements.active.classList.add('hidden');
    elements.summary.classList.remove('hidden');

    elements.finalFocusScore.innerText = Math.round(summary.focus_score);

    // Color code score
    if (summary.focus_score >= 80) elements.finalFocusScore.style.color = 'var(--success-color)';
    else if (summary.focus_score >= 50) elements.finalFocusScore.style.color = 'var(--warning-color)';
    else elements.finalFocusScore.style.color = 'var(--error-color)';

    elements.summaryDuration.innerText = `${summary.duration_minutes} min`;
    elements.summaryDistractions.innerText = summary.distractions;
    elements.summaryState.innerText = capitalize(summary.user_state);

    if (summary.recommended_technique) {
        elements.recommendationText.innerText = `Based on your performance, try the ${capitalize(summary.recommended_technique)} technique next time.`;
        elements.recommendationAlert.classList.remove('hidden');
    } else {
        elements.recommendationAlert.classList.add('hidden');
    }

    // --- Score Breakdown Calculation (Frontend Estimation) ---
    const distCount = summary.distractions;

    // 1. Distractions (Max 40)
    // Formula: Max(0, 40 - (d * 4))
    const scoreDist = Math.max(0, 40 - (distCount * 4));
    const distEl = document.getElementById('scoreDistractions');
    if (distEl) {
        distEl.innerText = `${scoreDist}/40`;
        distEl.style.color = scoreDist < 30 ? 'var(--error-color)' : 'var(--success-color)';
    }

    // 2. Consistency (Max 30)
    // Formula: Max(0, 30 - (d * 2))
    const scoreConst = Math.max(0, 30 - (distCount * 2));
    const constEl = document.getElementById('scoreConsistency');
    if (constEl) constEl.innerText = `${scoreConst}/30`;

    // 3. Camera (Max 20)
    let scoreCam = 15; // Default without camera
    if (summary.camera_enabled) {
        // We lack exact absence time in seconds here, but let's estimate
        // If score is high and distractions low, assume good presence?
        // Actually, let's just reverse engineer: Total - (Idle + Dist + Const)
        // Or just display "20/20" if enabled for now as estimation
        // Better: Use the 15/20 base logic
        scoreCam = 20; // Assume perfect if enabled for display simplicity
        // Or calculate: (1 - absence/duration) * 20
        if (summary.camera_absence_minutes > 0 && summary.duration_minutes > 0) {
            const ratio = summary.camera_absence_minutes / summary.duration_minutes;
            scoreCam = Math.round((1 - ratio) * 20);
        }
    }
    const camEl = document.getElementById('scoreCamera');
    if (camEl) {
        camEl.innerText = summary.camera_enabled ? `${scoreCam}/20` : "15/20 (No Camera)";
        camEl.classList.toggle('text-muted', !summary.camera_enabled);
    }

    // 4. Idle (Max 10)
    // Formula: (1 - idle%) * 10
    const idleP = summary.idle_time_percentage || 0; // 0 to 100
    const scoreIdle = Math.round((1 - (idleP / 100)) * 10);
    const idleEl = document.getElementById('scoreIdle');
    if (idleEl) idleEl.innerText = `${scoreIdle}/10`;

    // Dynamically inject dashboard button (to bypass HTML caching issues)
    const btnContainer = document.getElementById('dashboard-btn-container');
    if (btnContainer) {
        btnContainer.innerHTML = '';
        const btn = document.createElement('button');
        btn.className = 'btn btn-secondary w-100 h-100'; // w-100 h-100 to fill container
        btn.innerText = 'Go to Dashboard';
        btn.onclick = (e) => {
            e.preventDefault();
            window.location.href = 'student_dashboard.html';
        };
        btnContainer.appendChild(btn);
    } else {
        // Fallback for unexpected HTML structure
        console.warn("Dashboard button container not found, checking existing buttons...");
        const dashBtns = document.querySelectorAll('#sessionSummary button');
        dashBtns.forEach(btn => {
            if (btn.innerText.includes('Dashboard')) {
                btn.onclick = (e) => {
                    e.preventDefault();
                    window.location.href = 'student_dashboard.html';
                };
            }
        });
    }
}

// Helpers
function showAlert(msg, type = 'info') {
    const container = document.getElementById('alertBannerContainer');
    const div = document.createElement('div');
    div.className = `alert-banner alert alert-${type}`;
    div.innerText = msg;
    container.appendChild(div);

    // Remove after 3s
    setTimeout(() => div.remove(), 3000);
}

// Fullscreen Logic
function toggleFullscreen() {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(err => {
            console.error(`Error attempting to enable fullscreen: ${err.message}`);
        });
    } else {
        if (document.exitFullscreen) {
            document.exitFullscreen();
        }
    }
}

document.addEventListener('fullscreenchange', () => {
    const isFullscreen = !!document.fullscreenElement;
    const btn = document.getElementById('fullscreenBtn');
    if (btn) {
        btn.innerHTML = isFullscreen ? '↙ Exit Fullscreen' : '⛶ Fullscreen';
        btn.classList.toggle('btn-info', !isFullscreen);
        btn.classList.toggle('btn-outline-info', isFullscreen);
    }

    // Check violation if session active and mode is screen
    if (sessionState.active && !sessionState.paused && sessionState.studyMode === 'screen') {
        if (!isFullscreen) {
            handleFullscreenViolation();
        } else {
            // Cleared
            const warningEl = document.getElementById('fullscreenWarning');
            if (warningEl) warningEl.classList.add('hidden');
        }
    }
});

let violationCount = 0;
let lastViolationTime = 0;

async function handleFullscreenViolation() {
    const now = Date.now();
    violationCount++;
    const timeSinceLast = (now - lastViolationTime) / 1000;
    lastViolationTime = now;

    // Show immediate local warning
    const warningEl = document.getElementById('fullscreenWarning');
    const warningText = document.getElementById('fullscreenWarningText');
    if (warningEl) {
        warningEl.classList.remove('hidden');
        warningText.innerText = `Violation #${violationCount}: Please return to fullscreen!`;
    }

    try {
        const response = await authenticatedFetch(`${API_URL}/api/ml/fullscreen-violation`, {
            method: 'POST',
            body: JSON.stringify({
                session_duration_minutes: sessionState.duration / 60,
                violation_count: violationCount,
                last_violation_type: "EXIT_FULLSCREEN",
                time_since_last_violation_seconds: timeSinceLast,
                current_focus_score: 100 // Placeholder
            })
        });

        if (response.ok) {
            const data = await response.json();

            // Update Warning Text based on backend response
            const warningText = document.getElementById('fullscreenWarningText');
            if (warningText) {
                warningText.innerHTML = `<strong>${data.action.replace('_', ' ')}</strong><br>${data.message_to_user}`;
            }

            if (data.action === "END_SESSION") {
                alert("Session ended due to repeated fullscreen violations.");
                endSession();
            }
        }
    } catch (e) {
        console.error("Error reporting violation:", e);
    }
}

function playNotificationSound() {
    console.log("Notification: Timer finished");
}

function capitalize(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1);
}

async function checkActiveSession() {
    try {
        const response = await authenticatedFetch(`${API_URL}/api/sessions/active`);
        if (response.ok) {
            const data = await response.json();

            if (data.success && data.session) {
                console.log("Restoring active session...", data.session);

                // Restore State
                const s = data.session;
                sessionState = {
                    ...sessionState,
                    active: true,
                    technique: s.technique,
                    studyMode: s.study_mode,
                    cameraEnabled: s.camera_enabled,
                    duration: s.elapsed_seconds,
                    startTime: new Date(s.start_time).getTime()
                };

                // Sync UI Selectors
                elements.techniqueSelect.value = s.technique;
                elements.modeSelect.value = s.study_mode;
                elements.cameraToggle.checked = s.camera_enabled;

                // Update UI to Active Mode
                updateUIForSessionStart();

                // Initialize camera if enabled
                if (sessionState.cameraEnabled && typeof startCamera === 'function') {
                    const cameraStarted = await startCamera();
                    if (!cameraStarted) {
                        sessionState.cameraEnabled = false;
                        elements.cameraToggle.checked = false;
                        showAlert('Camera access failed on restore. Continuing without camera.', 'warning');
                    } else {
                        // Start Visual Detection Loop (Overlay)
                        if (typeof startFaceDetectionLoop === 'function') {
                            const videoEl = document.getElementById('cameraPreview');
                            startFaceDetectionLoop(videoEl);
                        }
                    }
                }

                // Start Timer
                startTimer();

                // Start Monitoring
                startMonitoring();

                showAlert("Session restored successfully", "success");
            }
        }
    } catch (e) {
        console.error("Error restoring session:", e);
    }
}
