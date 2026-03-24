/**
 * FocusFlow - Discussion Forum Chat Module
 * Handles all private messaging logic with strict privacy enforcement.
 * Only the two participants of a chat can ever see its messages.
 */

let currentContactId = null;
let currentContactName = '';
let currentUser = null;
let allContacts = [];
let pollInterval = null;

// ── Boot ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    // Verify authentication - redirect if not logged in
    if (!await protectPage()) return;

    currentUser = getUser();

    // Set back button href based on role
    const backBtn = document.getElementById('backBtn');
    if (currentUser) {
        if (currentUser.role === 'teacher') {
            backBtn.href = 'teacher_dashboard.html';
        } else {
            backBtn.href = 'student_dashboard.html';
        }
    }

    await loadContacts();

    // Send on Enter key
    const input = document.getElementById('messageInput');
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            document.getElementById('messageForm').dispatchEvent(new Event('submit'));
        }
    });
});

// ── Load Contacts ─────────────────────────────────────────────────────────────
async function loadContacts() {
    try {
        const response = await authenticatedFetch(`${API_URL}/api/chat/contacts`);
        if (!response.ok) throw new Error('Failed to load contacts');

        allContacts = await response.json();
        renderContacts(allContacts);
    } catch (error) {
        console.error('Error loading contacts:', error);
        document.getElementById('contactsList').innerHTML = `
            <div class="no-contacts">
                <div class="icon">⚠️</div>
                <p>Failed to load contacts.<br>Make sure you are enrolled in a classroom.</p>
            </div>
        `;
    }
}

// ── Render Contacts ───────────────────────────────────────────────────────────
function renderContacts(contacts) {
    const list = document.getElementById('contactsList');

    if (!contacts || contacts.length === 0) {
        list.innerHTML = `
            <div class="no-contacts">
                <div class="icon">👥</div>
                <p>No contacts yet.<br>Join or create a classroom to chat with classmates and teachers.</p>
            </div>
        `;
        return;
    }

    list.innerHTML = '';

    contacts.forEach(contact => {
        const initial = contact.username.charAt(0).toUpperCase();
        const roleClass = contact.role === 'teacher' ? 'teacher' : 'student';
        const roleLabel = contact.role === 'teacher' ? '👨‍🏫 Teacher' : '🎓 Student';
        const unreadHtml = (contact.unread_count > 0)
            ? `<div class="unread-badge">${contact.unread_count > 99 ? '99+' : contact.unread_count}</div>`
            : '';

        const item = document.createElement('div');
        item.className = `contact-item${contact.id === currentContactId ? ' active' : ''}`;
        item.dataset.contactId = contact.id;
        item.dataset.username = contact.username.toLowerCase();
        item.onclick = () => openChat(contact.id, contact.username, contact.role);

        item.innerHTML = `
            <div class="contact-avatar ${roleClass}">${initial}</div>
            <div class="contact-info">
                <div class="contact-name">${escapeHtml(contact.username)}</div>
                <span class="contact-role-badge ${roleClass}">${roleLabel}</span>
            </div>
            ${unreadHtml}
        `;

        list.appendChild(item);
    });
}

// ── Filter Contacts ───────────────────────────────────────────────────────────
function filterContacts(query) {
    const q = query.toLowerCase().trim();
    const filtered = q ? allContacts.filter(c => c.username.toLowerCase().includes(q)) : allContacts;
    renderContacts(filtered);
    // Re-mark active
    if (currentContactId) {
        const activeItem = document.querySelector(`.contact-item[data-contact-id="${currentContactId}"]`);
        if (activeItem) activeItem.classList.add('active');
    }
}

// ── Open Chat ─────────────────────────────────────────────────────────────────
async function openChat(contactId, contactName, contactRole) {
    // Stop previous polling
    if (pollInterval) clearInterval(pollInterval);

    currentContactId = contactId;
    currentContactName = contactName;

    // Update header
    const roleClass = contactRole === 'teacher' ? 'teacher' : 'student';
    document.getElementById('chatAvatar').className = `contact-avatar ${roleClass}`;
    document.getElementById('chatAvatar').style.cssText = 'width:38px;height:38px;font-size:0.95rem;';
    document.getElementById('chatAvatar').textContent = contactName.charAt(0).toUpperCase();
    document.getElementById('chatName').textContent = contactName;
    document.getElementById('chatRole').textContent = contactRole === 'teacher' ? '👨‍🏫 Teacher' : '🎓 Student';

    // Mark active in sidebar
    document.querySelectorAll('.contact-item').forEach(item => {
        item.classList.toggle('active', parseInt(item.dataset.contactId) === contactId);
    });

    // Show input area
    document.getElementById('messageInputArea').style.display = 'block';
    document.getElementById('messageInput').focus();

    // Load messages
    await loadMessages();

    // Mark as read
    await authenticatedFetch(`${API_URL}/api/chat/read/${contactId}`, { method: 'POST' });

    // Refresh contacts to clear unread badge
    loadContacts();

    // Poll for new messages every 4 seconds
    pollInterval = setInterval(async () => {
        await loadMessages(true); // silent refresh
        loadContacts(); // refresh unread counts
    }, 4000);
}

// ── Load Messages ─────────────────────────────────────────────────────────────
async function loadMessages(silent = false) {
    if (!currentContactId) return;

    if (!silent) {
        document.getElementById('messagesContainer').innerHTML = `
            <div class="empty-state">
                <div class="loading-dot">
                    <span></span><span></span><span></span>
                </div>
            </div>
        `;
    }

    try {
        const response = await authenticatedFetch(`${API_URL}/api/chat/history/${currentContactId}`);
        if (!response.ok) throw new Error('Failed to load messages');

        const messages = await response.json();
        renderMessages(messages, silent);
    } catch (error) {
        console.error('Error loading messages:', error);
        if (!silent) {
            document.getElementById('messagesContainer').innerHTML = `
                <div class="empty-state">
                    <div class="icon">⚠️</div>
                    <h4>Could not load messages</h4>
                    <p>Please try again.</p>
                </div>
            `;
        }
    }
}

// ── Render Messages ───────────────────────────────────────────────────────────
function renderMessages(messages, silent = false) {
    const container = document.getElementById('messagesContainer');
    const wasAtBottom = container.scrollHeight - container.clientHeight <= container.scrollTop + 50;

    if (!messages || messages.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="icon">💬</div>
                <h4>No messages yet</h4>
                <p>Say hello to <strong>${escapeHtml(currentContactName)}</strong>! This conversation is completely private — only the two of you can see it.</p>
            </div>
        `;
        return;
    }

    let html = '';
    let lastDate = '';

    messages.forEach(msg => {
        const isMe = parseInt(msg.sender_id) === parseInt(currentUser.id);
        const msgDate = formatDate(msg.created_at);
        const msgTime = formatTime(msg.created_at);

        // Date separator
        if (msgDate !== lastDate) {
            html += `
                <div class="date-separator">
                    <span>${msgDate}</span>
                </div>
            `;
            lastDate = msgDate;
        }

        const initial = msg.sender_name.charAt(0).toUpperCase();
        const avatarClass = isMe ? 'me-avatar' : 'them-avatar';
        const wrapperClass = isMe ? 'me' : 'them';

        html += `
            <div class="message-wrapper ${wrapperClass}">
                <div class="msg-avatar ${avatarClass}">${initial}</div>
                <div>
                    <div class="message-bubble">${escapeHtml(msg.content)}</div>
                    <div class="message-time">${msgTime}</div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;

    // Auto-scroll to bottom if user was already near bottom
    if (!silent || wasAtBottom) {
        container.scrollTop = container.scrollHeight;
    }
}

// ── Send Message ──────────────────────────────────────────────────────────────
async function sendMessage(event) {
    event.preventDefault();

    const input = document.getElementById('messageInput');
    const content = input.value.trim();

    if (!content || !currentContactId) return;

    const sendBtn = document.getElementById('sendBtn');
    sendBtn.disabled = true;

    // Optimistically clear the input
    input.value = '';
    input.style.height = 'auto';

    try {
        const response = await authenticatedFetch(`${API_URL}/api/chat/send`, {
            method: 'POST',
            body: JSON.stringify({
                receiver_id: currentContactId,
                content: content
            })
        });

        if (!response.ok) throw new Error('Failed to send');

        // Reload messages to show the new one
        await loadMessages(false);
    } catch (error) {
        console.error('Error sending message:', error);
        input.value = content; // Restore on failure
        alert('Failed to send message. Please try again.');
    } finally {
        sendBtn.disabled = false;
        input.focus();
    }
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function escapeHtml(text) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
}

function formatDate(isoString) {
    const date = new Date(isoString);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    if (date.toDateString() === today.toDateString()) return 'Today';
    if (date.toDateString() === yesterday.toDateString()) return 'Yesterday';

    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function formatTime(isoString) {
    return new Date(isoString).toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
    });
}
