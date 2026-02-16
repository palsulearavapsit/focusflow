/**
 * FocusFlow Dashboard Logic
 * Fetches and displays user statistics and session history
 */

let focusHistoryChart = null;
let focusQualityChart = null;

document.addEventListener('DOMContentLoaded', async () => {
    // Auth check
    if (!await protectPage('student')) return;

    // Display user info from auth.js helper
    displayUserInfo();

    // Load data
    loadHistory();
    loadClassrooms();
    checkActiveSessionStatus();
});

// ... (existing functions)

// Join Classroom Logic
async function loadClassrooms() {
    try {
        const response = await authenticatedFetch(`${API_URL}/api/classrooms/student/list`);
        if (!response.ok) throw new Error('Failed to load classrooms');

        const classrooms = await response.json();
        renderClassrooms(classrooms);
    } catch (error) {
        console.error('Error loading classrooms:', error);
        document.getElementById('classroomsList').innerHTML = `<p class="text-danger text-center">Failed to load classrooms.</p>`;
    }
}

function renderClassrooms(classrooms) {
    const list = document.getElementById('classroomsList');
    list.innerHTML = '';

    if (classrooms.length === 0) {
        list.innerHTML = `
            <div class="col-12 text-center text-secondary">
                <p>You haven't joined any classrooms yet.</p>
            </div>
        `;
        return;
    }

    classrooms.forEach(cls => {
        const roleBadge = cls.role === 'representative'
            ? '<span class="badge bg-warning text-dark ms-2">Representative</span>'
            : '<span class="badge bg-secondary ms-2">Student</span>';

        const item = `
             <div class="col-md-6 col-lg-4">
                <div class="card p-3 border-secondary h-100" style="background: var(--bg-tertiary);">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <h5 class="mb-0">
                            <a href="student_classroom.html?id=${cls.id}" class="text-white text-decoration-none stretched-link-except">${cls.name}</a>
                        </h5>
                    </div>
                    <p class="text-secondary small mb-2">Teacher: ${cls.teacher_name || 'Unknown'}</p>
                    <div class="d-flex justify-content-between align-items-center mt-2">
                        <div>
                            <span class="badge bg-success">Joined</span>
                            ${roleBadge}
                        </div>
                        <button class="btn btn-sm btn-outline-danger" onclick="leaveClassroom(${cls.id}, '${cls.name}')">Leave</button>
                    </div>
                </div>
            </div>
        `;
        list.insertAdjacentHTML('beforeend', item);
    });
}

async function leaveClassroom(id, name) {
    if (!confirm(`Are you sure you want to leave "${name}"? You will need the code to join again.`)) return;

    try {
        const response = await authenticatedFetch(`${API_URL}/api/classrooms/${id}/leave`, {
            method: 'DELETE'
        });

        if (!response.ok) throw new Error('Failed to leave classroom');

        loadClassrooms(); // Reload list
    } catch (error) {
        alert('Error leaving classroom');
        console.error(error);
    }
}

// Handle Join Form
document.getElementById('joinClassForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const code = document.getElementById('classCode').value;

    try {
        const btn = e.target.querySelector('button');
        const originalText = btn.innerText;
        btn.disabled = true;
        btn.innerText = 'Joining...';

        const response = await authenticatedFetch(`${API_URL}/api/classrooms/join`, {
            method: 'POST',
            body: JSON.stringify({ code })
        });

        const data = await response.json();

        if (!response.ok) throw new Error(data.detail || 'Failed to join');

        alert(`Successfully joined: ${data.message}`);

        // Close modal and reload
        const modal = bootstrap.Modal.getInstance(document.getElementById('joinClassModal'));
        modal.hide();
        document.getElementById('classCode').value = '';
        loadClassrooms();

    } catch (error) {
        alert(error.message);
    } finally {
        const btn = e.target.querySelector('button');
        btn.disabled = false;
        btn.innerText = 'Join';
    }
});

async function checkActiveSessionStatus() {
    try {
        const response = await authenticatedFetch(`${API_URL}/api/sessions/active`);
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                const startBtn = document.querySelector('.btn-primary'); // "+ Start New Session" button
                if (startBtn) {
                    startBtn.innerText = "▶ Resume Active Session";
                    startBtn.classList.remove('btn-primary');
                    startBtn.classList.add('btn-warning'); // Make it stand out
                    startBtn.onclick = (e) => {
                        e.preventDefault();
                        window.location.href = 'study.html';
                    };
                }
            }
        }
    } catch (e) {
        console.error("Error checking active session:", e);
    }
}

async function loadHistory() {
    try {
        const response = await authenticatedFetch(`${API_URL}/api/sessions/history?limit=20`);
        if (!response.ok) throw new Error('Failed to fetch history');

        const sessions = await response.json();

        updateStats(sessions);
        renderCharts(sessions);
        renderTable(sessions.slice(0, 10)); // Show only 10 in table

    } catch (error) {
        console.error('Dashboard error:', error);
        document.getElementById('sessionsTableBody').innerHTML = `
            <tr><td colspan="6" class="text-center py-4 text-danger">Error loading data. Please try again.</td></tr>
        `;
    }
}

function updateStats(sessions) {
    // Calculate stats locally from recent history (or separate API call ideally)
    // For now, simple client-side aggregation

    const totalSessions = sessions.length;
    const totalTimeSec = sessions.reduce((acc, s) => acc + s.duration, 0);
    const avgScore = totalSessions > 0
        ? sessions.reduce((acc, s) => acc + s.focus_score, 0) / totalSessions
        : 0;

    document.getElementById('totalSessions').innerText = totalSessions;
    document.getElementById('avgFocusScore').innerText = Math.round(avgScore);
    document.getElementById('totalStudyTime').innerText = formatDuration(totalTimeSec);

    // Calculate Active Streak
    let streak = 0;
    if (sessions.length > 0) {
        const uniqueDates = [...new Set(sessions.map(s => new Date(s.timestamp).toDateString()))];
        // Sort dates descending
        uniqueDates.sort((a, b) => new Date(b) - new Date(a));

        const today = new Date().toDateString();
        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);
        const yesterdayStr = yesterday.toDateString();

        // Check if studied today or yesterday to start streak
        if (uniqueDates[0] === today || uniqueDates[0] === yesterdayStr) {
            streak = 1;
            let currentDate = new Date(uniqueDates[0]);

            for (let i = 1; i < uniqueDates.length; i++) {
                const prevDate = new Date(uniqueDates[i]);
                const diffTime = Math.abs(currentDate - prevDate);
                const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

                if (diffDays === 1) {
                    streak++;
                    currentDate = prevDate;
                } else {
                    break;
                }
            }
        }
    }
    document.getElementById('activeStreak').innerText = `${streak} days`;
}

function renderTable(sessions) {
    const tbody = document.getElementById('sessionsTableBody');
    tbody.innerHTML = '';

    if (sessions.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center py-4 text-muted">No sessions found. Start studying!</td></tr>`;
        return;
    }

    sessions.forEach(session => {
        const date = new Date(session.timestamp).toLocaleDateString();
        const scoreClass = getScoreClass(session.focus_score);

        const row = `
            <tr>
                <td>${date}</td>
                <td>${capitalize(session.technique)}</td>
                <td>${capitalize(session.study_mode)}</td>
                <td>${Math.round(session.duration / 60)} min</td>
                <td><span class="badge ${scoreClass}">${Math.round(session.focus_score)}</span></td>
                <td>${capitalize(session.user_state || 'Completed')}</td>
            </tr>
        `;
        tbody.insertAdjacentHTML('beforeend', row);
    });
}

function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    if (hours > 0) return `${hours}h ${mins}m`;
    if (mins > 0) return `${mins}m`;
    return `${secs}s`;
}

function getScoreClass(score) {
    if (score >= 80) return 'badge-success';
    if (score >= 50) return 'badge-warning';
    return 'badge-error';
}

function capitalize(str) {
    if (!str) return '';
    return str.replace('-', ' ').replace(/\b\w/g, c => c.toUpperCase());
}

// Sidebar Toggle Logic
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('mainContent');
    const toggleBtn = sidebar.querySelector('.sidebar-toggle-btn span');

    sidebar.classList.toggle('collapsed');
    mainContent.classList.toggle('expanded');

    // Rotate arrow
    if (sidebar.classList.contains('collapsed')) {
        toggleBtn.innerText = "▶";
    } else {
        toggleBtn.innerText = "◀";
    }
}

function toggleSidebarMobile() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('open');
}

function renderCharts(sessions) {
    if (sessions.length === 0) return;

    // 1. Focus History Chart (Line)
    const ctxHistory = document.getElementById('focusHistoryChart');
    if (ctxHistory) {
        // Reverse sessions to show oldest to newest
        const sortedSessions = [...sessions].reverse();
        const labels = sortedSessions.map(s => new Date(s.timestamp).toLocaleDateString());
        const data = sortedSessions.map(s => Math.round(s.focus_score));

        if (focusHistoryChart) focusHistoryChart.destroy();

        focusHistoryChart = new Chart(ctxHistory, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Focus Score',
                    data: data,
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99, 102, 241, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointBackgroundColor: '#8b5cf6'
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        grid: { color: '#334155' },
                        ticks: { color: '#cbd5e1' }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#cbd5e1' }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }

    // 2. Focus Quality Chart (Doughnut)
    const ctxQuality = document.getElementById('focusQualityChart');
    if (ctxQuality) {
        const high = sessions.filter(s => s.focus_score >= 80).length;
        const med = sessions.filter(s => s.focus_score >= 50 && s.focus_score < 80).length;
        const low = sessions.filter(s => s.focus_score < 50).length;

        if (focusQualityChart) focusQualityChart.destroy();

        focusQualityChart = new Chart(ctxQuality, {
            type: 'doughnut',
            data: {
                labels: ['High Focus (>80)', 'Medium (50-80)', 'Low (<50)'],
                datasets: [{
                    data: [high, med, low],
                    backgroundColor: ['#10b981', '#f59e0b', '#ef4444'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#cbd5e1' }
                    }
                }
            }
        });
    }
}
