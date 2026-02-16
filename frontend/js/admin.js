/**
 * FocusFlow Admin Dashboard Logic
 * Fetches and displays system-wide statistics and user data
 */

document.addEventListener('DOMContentLoaded', async () => {
    // Auth check (strict admin)
    if (!await protectPage('admin')) return;

    // Load data
    loadAdminData();
    loadUsers();

    // Auto-refresh every 30 seconds for "real-time" updates
    setInterval(() => {
        loadAdminData();
    }, 30000);

    // Search filter
    document.getElementById('userSearch').addEventListener('input', (e) => {
        const term = e.target.value.toLowerCase();
        filterUsers(term);
    });
});

let allUsers = []; // Store locally for filtering

async function loadAdminData() {
    try {
        const response = await authenticatedFetch(`${API_URL}/api/admin/dashboard-summary`);
        if (!response.ok) throw new Error('Failed to fetch admin stats');

        const summary = await response.json();
        const overview = summary.overview || {};

        document.getElementById('totalStudents').innerText = summary.total_users || 0;
        document.getElementById('totalSessions').innerText = overview.total_sessions || 0;
        document.getElementById('globalAvgScore').innerText = overview.overall_avg_focus_score ? Math.round(overview.overall_avg_focus_score) : 0;

        // Real data
        document.getElementById('activeCameras').innerText = overview.sessions_with_camera_enabled || 0;
        document.getElementById('popularTechnique').innerText = overview.most_popular_technique || "N/A";
        document.getElementById('popularMode').innerText = overview.most_popular_mode || "N/A";

    } catch (error) {
        console.error('Admin stats error:', error);
    }
}

async function loadUsers() {
    try {
        const response = await authenticatedFetch(`${API_URL}/api/admin/users`);
        console.log("Admin Users Loaded (v4)");
        if (!response.ok) throw new Error('Failed to fetch users');

        allUsers = await response.json();
        renderUsersTable(allUsers);

    } catch (error) {
        console.error('User list error:', error);
        document.getElementById('usersTableBody').innerHTML = `
            <tr><td colspan="5" class="text-center text-danger">Error loading users</td></tr>
        `;
    }
}

function filterUsers(term) {
    if (!term) {
        renderUsersTable(allUsers);
        return;
    }
    const filtered = allUsers.filter(u =>
        u.username.toLowerCase().includes(term) ||
        u.email.toLowerCase().includes(term)
    );
    renderUsersTable(filtered);
}

function renderUsersTable(users) {
    const tbody = document.getElementById('usersTableBody');
    tbody.innerHTML = '';

    if (users.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center">No users found</td></tr>`;
        return;
    }

    const currentUser = getUser(); // from auth.js

    users.forEach(user => {
        const joined = new Date(user.created_at).toLocaleDateString();
        const isSelf = user.id === currentUser.id;

        let roleBadge = '';
        if (user.role === 'admin') roleBadge = '<span class="badge badge-warning">ADMIN</span>';
        else if (user.role === 'teacher') roleBadge = '<span class="badge badge-info">TEACHER</span>';
        else roleBadge = '<span class="badge badge-secondary">STUDENT</span>';

        // Role Action
        let roleAction = '';
        if (!isSelf && user.role !== 'admin') {
            const nextRole = user.role === 'student' ? 'teacher' : 'student';
            const btnClass = user.role === 'student' ? 'btn-outline-info' : 'btn-outline-secondary';
            const label = user.role === 'student' ? 'Make Teacher' : 'Make Student';
            roleAction = `<button class="btn btn-sm ${btnClass} me-1" onclick="updateUserRole(${user.id}, '${nextRole}')">${label}</button>`;
        }

        // Delete Action
        let deleteAction = '';
        if (!isSelf) {
            deleteAction = `<button class="btn btn-sm btn-outline-danger" onclick="deleteUser(${user.id}, '${user.username}')">Delete</button>`;
        }

        const row = `
            <tr>
                <td>#${user.id}</td>
                <td>
                    <div class="d-flex align-items-center gap-2">
                        <span class="avatar-circle small" style="width:24px;height:24px;font-size:0.7rem;">${user.username.charAt(0).toUpperCase()}</span>
                        ${user.username}
                    </div>
                </td>
                <td>${user.email}</td>
                <td>${roleBadge}</td>
                <td>
                    <div class="d-flex gap-2">
                        <button class="btn btn-sm btn-outline btn-secondary" onclick="viewUserStats(${user.id})">Stats</button>
                        ${roleAction}
                        ${deleteAction}
                    </div>
                </td>
            </tr>
        `;
        tbody.insertAdjacentHTML('beforeend', row);
    });
}

async function updateUserRole(userId, newRole) {
    if (!confirm(`Are you sure you want to change this user's role to ${newRole.toUpperCase()}?`)) return;

    try {
        const response = await authenticatedFetch(`${API_URL}/api/admin/users/${userId}/role`, {
            method: 'PUT',
            body: JSON.stringify({ role: newRole })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to update role');
        }

        alert(`User role updated to ${newRole}`);
        loadUsers();

    } catch (error) {
        alert(error.message);
    }
}

async function deleteUser(userId, username) {
    if (!confirm(`WARNING: Are you sure you want to PERMANENTLY DELETE user "${username}"? This action cannot be undone.`)) return;

    try {
        const response = await authenticatedFetch(`${API_URL}/api/admin/users/${userId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to delete user');
        }

        loadUsers();

    } catch (error) {
        alert(error.message);
    }
}

async function viewUserStats(userId) {
    const modalElement = document.getElementById('userStatsModal');
    const modal = new bootstrap.Modal(modalElement);
    modal.show();

    const content = document.getElementById('userStatsContent');
    content.innerHTML = `
        <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
    `;

    try {
        const response = await authenticatedFetch(`${API_URL}/api/admin/user-statistics`);
        if (!response.ok) throw new Error('Failed to fetch user stats');

        const allStats = await response.json();
        const userStats = allStats.find(s => s.user_id === userId);

        if (!userStats) {
            content.innerHTML = `<p class="text-muted">No sessions recorded for this user yet.</p>`;
            return;
        }

        content.innerHTML = `
            <div class="row text-start p-3">
                <div class="col-md-6 mb-3">
                    <strong class="text-secondary">Total Sessions:</strong> 
                    <h4 class="text-white">${userStats.total_sessions}</h4>
                </div>
                <div class="col-md-6 mb-3">
                    <strong class="text-secondary">Total Study Time:</strong> 
                    <h4 class="text-white">${Math.round(userStats.total_study_time / 60)} min</h4>
                </div>
                <div class="col-md-6 mb-3">
                    <strong class="text-secondary">Avg Focus Score:</strong> 
                    <h4 class="text-primary">${userStats.avg_focus_score ? Math.round(userStats.avg_focus_score) : 0}</h4>
                </div>
                <div class="col-md-6 mb-3">
                    <strong class="text-secondary">Total Distractions:</strong> 
                    <h4 class="text-warning">${userStats.total_distractions}</h4>
                </div>
                 <div class="col-md-6 mb-3">
                    <strong class="text-secondary">Most Used Technique:</strong> 
                    <h5 class="text-info">${capitalize(userStats.most_used_technique)}</h5>
                </div>
                 <div class="col-md-6 mb-3">
                    <strong class="text-secondary">Sessions with Camera:</strong> 
                    <h5 class="text-success">${userStats.sessions_with_camera}</h5>
                </div>
            </div>
        `;

    } catch (error) {
        console.error('Error fetching user stats', error);
        content.innerHTML = `<p class="text-danger">Error loading data.</p>`;
    }
}

function capitalize(str) {
    if (!str) return 'N/A';
    return str.replace('-', ' ').replace(/\b\w/g, c => c.toUpperCase());
}

// Create User Logic
function showCreateUserModal() {
    const modal = new bootstrap.Modal(document.getElementById('createUserModal'));
    modal.show();
}

document.getElementById('createUserForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('newUsername').value;
    const email = document.getElementById('newEmail').value;
    const password = document.getElementById('newPassword').value;
    const role = document.getElementById('newRole').value;

    try {
        // Pass false for autoLogin to prevent admin session overwrite
        const result = await signup(username, email, password, role, false);

        if (result.success) {
            alert('User created successfully');
            bootstrap.Modal.getInstance(document.getElementById('createUserModal')).hide();
            // Reset form
            e.target.reset();
            loadUsers();
        } else {
            alert('Error: ' + result.error);
        }

    } catch (error) {
        alert('An unexpected error occurred');
        console.error(error);
    }
});

// Sidebar Toggle Logic
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('mainContent');
    const toggleBtn = sidebar.querySelector('.sidebar-toggle-btn span');

    sidebar.classList.toggle('collapsed');
    mainContent.classList.toggle('expanded');

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
