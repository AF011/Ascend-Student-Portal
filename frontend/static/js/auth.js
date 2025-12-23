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
        // ✅ FIXED: Changed to /auth/oauth_callback (was /auth/google/callback)
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