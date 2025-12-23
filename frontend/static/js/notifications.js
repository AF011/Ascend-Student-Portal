// notifications.js - Minimal notification handling
// Place in: frontend/static/js/notifications.js

let unreadCount = 0;

// Load unread count
async function loadUnreadCount() {
    try {
        const token = getToken();
        const response = await fetch('/api/v1/notifications/unread-count', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        const data = await response.json();
        
        if (data.success) {
            unreadCount = data.unread_count;
            updateBadge();
        }
    } catch (error) {
        console.error('Error loading unread count:', error);
    }
}

// Update notification badge
function updateBadge() {
    const badge = document.getElementById('notificationBadge');
    if (badge) {
        if (unreadCount > 0) {
            badge.textContent = unreadCount > 99 ? '99+' : unreadCount;
            badge.classList.remove('hidden');
        } else {
            badge.classList.add('hidden');
        }
    }
}

// Load notifications
async function loadNotifications() {
    try {
        const token = getToken();
        const response = await fetch('/api/v1/notifications?limit=10', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        const data = await response.json();
        
        if (data.success) {
            displayNotifications(data.notifications);
        }
    } catch (error) {
        console.error('Error loading notifications:', error);
    }
}

// Display notifications in dropdown
function displayNotifications(notifications) {
    const container = document.getElementById('notificationsList');
    if (!container) return;
    
    if (notifications.length === 0) {
        container.innerHTML = '<div class="p-4 text-center text-gray-500">No notifications</div>';
        return;
    }
    
    container.innerHTML = '';
    
    notifications.forEach(notif => {
        const div = document.createElement('div');
        div.className = `p-3 border-b hover:bg-gray-50 cursor-pointer ${!notif.is_read ? 'bg-blue-50' : ''}`;
        div.onclick = () => handleNotificationClick(notif);
        
        div.innerHTML = `
            <div class="flex justify-between items-start mb-1">
                <strong class="text-sm">${notif.title}</strong>
                ${!notif.is_read ? '<span class="w-2 h-2 bg-blue-600 rounded-full"></span>' : ''}
            </div>
            <p class="text-xs text-gray-600">${notif.message}</p>
            <p class="text-xs text-gray-400 mt-1">${formatTime(notif.created_at)}</p>
        `;
        
        container.appendChild(div);
    });
}

// Handle notification click
async function handleNotificationClick(notif) {
    // Mark as read
    await markAsRead([notif.id]);
    
    // Navigate to action URL
    if (notif.action_url) {
        // ✅ Check if job exists before navigating
        const jobId = notif.action_url.split('/').pop();
        
        // Try to load job first
        try {
            const token = getToken();
            const response = await fetch(`/api/v1/jobs/${jobId}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            
            if (response.ok) {
                window.location.href = notif.action_url;
            } else {
                showNotification('This job is no longer available', 'warning');
            }
        } catch (error) {
            showNotification('Error loading job', 'error');
        }
    }
}

// Mark notifications as read
async function markAsRead(notificationIds) {
    try {
        const token = getToken();
        const response = await fetch('/api/v1/notifications/mark-read', {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(notificationIds)
        });
        
        if (response.ok) {
            loadUnreadCount();
        }
    } catch (error) {
        console.error('Error marking as read:', error);
    }
}

// Mark all as read
async function markAllAsRead() {
    try {
        const token = getToken();
        const response = await fetch('/api/v1/notifications/mark-all-read', {
            method: 'PUT',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.ok) {
            showNotification('✅ All notifications marked as read', 'success');
            loadUnreadCount();
            loadNotifications();
        }
    } catch (error) {
        console.error('Error marking all as read:', error);
    }
}

// Toggle notification dropdown
function toggleNotifications() {
    const dropdown = document.getElementById('notificationDropdown');
    if (dropdown) {
        const isHidden = dropdown.classList.contains('hidden');
        dropdown.classList.toggle('hidden');
        
        if (isHidden) {
            loadNotifications();
        }
    }
}

// Format time
function formatTime(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return date.toLocaleDateString();
}

// Auto-refresh every 30 seconds
setInterval(loadUnreadCount, 30000);

// Load on page load
if (typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', () => {
        if (isLoggedIn()) {
            loadUnreadCount();
        }
    });
}