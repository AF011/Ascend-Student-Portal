// utils.js - Utility functions for Virtual CDC
// Place in: frontend/static/js/utils.js

// API Base URL - Use dynamic origin instead of hardcoded localhost
// This allows it to work in production too
if (typeof API_URL === 'undefined') {
    window.API_URL = window.location.origin + '/api/v1';
}

// Get JWT token from localStorage
function getToken() {
    const token = localStorage.getItem('access_token');
    // ✅ ADDED: Safe check for invalid tokens
    if (!token || token === 'null' || token === 'undefined' || token.trim() === '') {
        return null;
    }
    return token;
}

// Set JWT token
function setToken(token) {
    if (token) {
        localStorage.setItem('access_token', token);
    } else {
        localStorage.removeItem('access_token');
    }
}

// Remove JWT token
function removeToken() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
}

// Get user data
function getUser() {
    try {
        const userStr = localStorage.getItem('user');
        if (!userStr || userStr === 'null' || userStr === 'undefined') {
            return null;
        }
        return JSON.parse(userStr);
    } catch (e) {
        console.error('Error parsing user:', e);
        return null;
    }
}

// Set user data
function setUser(user) {
    if (user) {
        localStorage.setItem('user', JSON.stringify(user));
    } else {
        localStorage.removeItem('user');
    }
}

// API call with authentication
async function apiCall(endpoint, options = {}) {
    const token = getToken();

    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_URL}${endpoint}`, {
        ...options,
        headers
    });

    if (response.status === 401) {
        removeToken();
        window.location.href = '/auth/login';
        return;
    }

    return response;
}

// Show loading state
function showLoading(message = 'Loading...') {
    return `<div class="loading">${message}</div>`;
}

// Show error message
function showError(message) {
    return `<div class="error">${message}</div>`;
}

// Show success message
function showSuccess(message) {
    return `<div class="success">${message}</div>`;
}

// Check if user is logged in
function isLoggedIn() {
    return !!getToken();
}

// Check if profile is completed
function isProfileCompleted() {
    const user = getUser();
    return user && user.profile_completed;
}

// ✅ FIXED LOGOUT - Redirects properly
function logout() {
    if (confirm('Are you sure you want to logout?')) {
        // Clear all auth data
        removeToken();
        localStorage.clear(); // Clear everything to be safe
        
        // Redirect to home page (index.html)
        window.location.replace('/');  // Use replace to prevent back button issues
    }
}

// Google Login
async function loginWithGoogle(role) {
    try {
        const response = await fetch(`${API_URL}/auth/google/login?role=${role}`);
        const data = await response.json();

        if (data.auth_url) {
            // Store role for callback
            localStorage.setItem('login_role', role);
            // Redirect to Google OAuth
            window.location.href = data.auth_url;
        }
    } catch (error) {
        console.error('Login error:', error);
        alert('Login failed. Please try again.');
    }
}

// Handle OAuth Callback
async function handleOAuthCallback() {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    const state = urlParams.get('state'); // role from Google

    if (!code) {
        window.location.href = '/';
        return;
    }

    const role = state || localStorage.getItem('login_role') || 'student';

    try {
        const response = await fetch(`${API_URL}/auth/oauth_callback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code, role })
        });

        const data = await response.json();

        if (data.access_token) {
            // Save token and user data
            setToken(data.access_token);
            setUser(data.user);
            localStorage.removeItem('login_role');

            // Redirect based on profile completion
            if (data.user.profile_completed) {
                redirectToDashboard(data.user.role);
            } else {
                redirectToProfileForm(data.user.role);
            }
        } else {
            throw new Error('No access token received');
        }
    } catch (error) {
        console.error('Callback error:', error);
        alert('Authentication failed. Please try again.');
        window.location.href = '/';
    }
}

// Redirect to dashboard
function redirectToDashboard(role) {
    if (role === 'student') {
        window.location.href = '/student/dashboard';
    } else {
        window.location.href = '/institution/dashboard';
    }
}

// Redirect to profile form
function redirectToProfileForm(role) {
    if (role === 'student') {
        window.location.href = '/student/profile';
    } else {
        window.location.href = '/institution/profile';
    }
}

// ✅ ADDED: Show notification helper
function showNotification(message, type = 'info') {
    console.log(`${type.toUpperCase()}: ${message}`);
    
    if (type === 'error') {
        alert('❌ ' + message);
    }
}