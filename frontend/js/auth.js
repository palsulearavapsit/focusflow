/**
 * FocusFlow Authentication Module
 * Handles user authentication, token management, and session persistence
 */

const API_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000'
    : 'https://aravpal-focusflow-backend.hf.space';

// Token management
function getToken() {
    return localStorage.getItem('focusflow_token');
}

function setToken(token) {
    localStorage.setItem('focusflow_token', token);
}

function removeToken() {
    localStorage.removeItem('focusflow_token');
    localStorage.removeItem('focusflow_user');
}

function getUser() {
    const userStr = localStorage.getItem('focusflow_user');
    return userStr ? JSON.parse(userStr) : null;
}

function setUser(user) {
    localStorage.setItem('focusflow_user', JSON.stringify(user));
}

// Check if user is authenticated
function isAuthenticated() {
    return !!getToken();
}

// Check if user is admin
function isAdmin() {
    const user = getUser();
    return user && user.role === 'admin';
}

// Check if user is student
function isStudent() {
    const user = getUser();
    return user && user.role === 'student';
}

// Check if user is teacher
function isTeacher() {
    const user = getUser();
    return user && user.role === 'teacher';
}

// Signup function
async function signup(username, email, password, role = 'student', autoLogin = true) {
    try {
        const response = await fetch(`${API_URL}/api/auth/signup`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, email, password, role })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Signup failed');
        }

        if (autoLogin) {
            // Save token and user
            setToken(data.access_token);
            setUser(data.user);
        }

        return { success: true, user: data.user };
    } catch (error) {
        console.error('Signup error:', error);
        return { success: false, error: error.message };
    }
}

// Login function
async function login(email, password) {
    try {
        const response = await fetch(`${API_URL}/api/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Login failed');
        }

        // Save token and user
        setToken(data.access_token);
        setUser(data.user);

        return { success: true, user: data.user };
    } catch (error) {
        console.error('Login error:', error);
        return { success: false, error: error.message };
    }
}

// Logout function
function logout() {
    removeToken();
    window.location.href = 'index.html';
}

// Verify token
async function verifyToken() {
    const token = getToken();
    if (!token) return false;

    try {
        const response = await fetch(`${API_URL}/api/auth/verify`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            removeToken();
            return false;
        }

        const userData = await response.json();
        setUser(userData); // Update local user with latest data (streaks, titles, etc)

        return true;
    } catch (error) {
        console.error('Token verification error:', error);
        removeToken();
        return false;
    }
}

// Protect page (redirect if not authenticated)
async function protectPage(requiredRole = null) {
    if (!isAuthenticated()) {
        window.location.href = 'login.html';
        return false;
    }

    const valid = await verifyToken();
    if (!valid) {
        window.location.href = 'login.html';
        return false;
    }

    const user = getUser();

    // Check role if specified
    if (requiredRole === 'admin' && !isAdmin()) {
        alert('Access denied. Admin role required.');
        window.location.href = 'student_dashboard.html';
        return false;
    }

    if (requiredRole === 'student' && !isStudent()) {
        // Redirect to appropriate dashboard instead of alerting
        if (isTeacher()) window.location.href = 'teacher_dashboard.html';
        else if (isAdmin()) window.location.href = 'admin.html';
        else window.location.href = 'index.html';
        return false;
    }

    if (requiredRole === 'teacher' && !isTeacher()) {
        // Redirect to appropriate dashboard instead of alerting
        if (isStudent()) window.location.href = 'student_dashboard.html';
        else if (isAdmin()) window.location.href = 'admin.html';
        else window.location.href = 'index.html';
        return false;
    }

    return true;
}

// Make authenticated API request
async function authenticatedFetch(url, options = {}) {
    const token = getToken();

    if (!token) {
        throw new Error('No authentication token');
    }

    const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        ...options.headers
    };

    const response = await fetch(url, {
        ...options,
        headers
    });

    // Handle 401 Unauthorized
    if (response.status === 401) {
        removeToken();
        window.location.href = 'login.html';
        throw new Error('Session expired. Please login again.');
    }

    return response;
}

// Display user info in navbar
function displayUserInfo() {
    const user = getUser();
    if (!user) return;

    const userInfoElement = document.getElementById('userInfo');
    if (userInfoElement) {
        const titleHtml = user.title ? `<div class="user-title text-secondary" style="font-size: 0.75rem; font-weight: 500;">${user.title}</div>` : '';
        const roleBadge = user.role === 'admin' ? '' : `<span class="badge badge-primary ms-2" style="font-size: 0.6rem;">${user.role.toUpperCase()}</span>`;

        userInfoElement.innerHTML = `
            <div class="d-flex flex-column">
                <div class="d-flex align-items-center">
                    <span class="text-primary font-weight-bold">${user.username}</span>
                    ${roleBadge}
                </div>
                ${titleHtml}
            </div>
        `;
    }

    // Also update sidebar if present
    const sidebarName = document.getElementById('userName');
    const sidebarAvatar = document.getElementById('userAvatar');
    if (sidebarName) sidebarName.innerText = user.username;
    if (sidebarAvatar) sidebarAvatar.innerText = user.username.charAt(0).toUpperCase();

    // Add title to sidebar if possible
    const sidebarUserInfo = document.querySelector('.sidebar .user-info');
    if (sidebarUserInfo && user.title && user.role !== 'admin') {
        let titleEl = sidebarUserInfo.querySelector('.user-title-display');
        if (!titleEl) {
            titleEl = document.createElement('div');
            titleEl.className = 'user-title-display text-secondary';
            titleEl.style.fontSize = '0.7rem';
            titleEl.style.marginTop = '2px';
            sidebarUserInfo.appendChild(titleEl);
        }
        titleEl.innerText = user.title;
    }
}

// Initialize auth on page load
document.addEventListener('DOMContentLoaded', () => {
    displayUserInfo();
});
