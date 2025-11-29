// RAG System Frontend JavaScript - High Fidelity ChatGPT Replica
const API_BASE = '';

// Check authentication status on page load
document.addEventListener('DOMContentLoaded', function () {
    checkStatus();
    checkAuthStatus();
    loadChatHistory();

    // Sidebar Toggle
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const mobileSidebarToggle = document.getElementById('mobileSidebarToggle');

    function toggleSidebar() {
        sidebar.classList.toggle('active');
    }

    if (sidebarToggle) sidebarToggle.addEventListener('click', toggleSidebar);
    if (mobileSidebarToggle) mobileSidebarToggle.addEventListener('click', toggleSidebar);

    // New Chat Button
    document.getElementById('newChatBtn').addEventListener('click', resetChat);

    // Auto-expand textarea
    const queryInput = document.getElementById('queryInput');
    const submitBtn = document.getElementById('submitBtn');

    queryInput.addEventListener('input', function () {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
        if (this.value === '') this.style.height = 'auto';

        // Enable/Disable submit button
        submitBtn.disabled = this.value.trim() === '' && !selectedImageBase64;
    });

    // Submit on Enter (Shift+Enter for newline)
    queryInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (this.value.trim() !== '' || selectedImageBase64) {
                handleQuery(e);
            }
        }
    });

    // Query form submission
    document.getElementById('queryForm').addEventListener('submit', handleQuery);

    // Image Upload Logic
    const imageInput = document.getElementById('imageInput');
    const btnAttach = document.querySelector('.btn-attach');
    const imagePreviewContainer = document.getElementById('imagePreviewContainer');
    const imagePreview = document.getElementById('imagePreview');
    const removeImageBtn = document.getElementById('removeImageBtn');

    btnAttach.addEventListener('click', () => imageInput.click());

    imageInput.addEventListener('change', function () {
        const file = this.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function (e) {
                selectedImageBase64 = e.target.result.split(',')[1]; // Remove prefix
                imagePreview.src = e.target.result;
                imagePreviewContainer.style.display = 'block';
                submitBtn.disabled = false;
            };
            reader.readAsDataURL(file);
        }
    });

    removeImageBtn.addEventListener('click', () => {
        selectedImageBase64 = null;
        imageInput.value = '';
        imagePreviewContainer.style.display = 'none';
        submitBtn.disabled = queryInput.value.trim() === '';
    });

    // Auth Buttons
    const loginBtn = document.getElementById('loginBtn');
    const registerBtn = document.getElementById('registerBtn');

    if (loginBtn) loginBtn.addEventListener('click', () => showModal('loginModal'));
    if (registerBtn) registerBtn.addEventListener('click', () => showModal('registerModal'));

    // Modal close buttons
    document.getElementById('closeLoginModal').addEventListener('click', () => hideModal('loginModal'));
    document.getElementById('closeRegisterModal').addEventListener('click', () => hideModal('registerModal'));

    // Login/Register forms
    document.getElementById('loginForm').addEventListener('submit', handleLogin);
    document.getElementById('registerForm').addEventListener('submit', handleRegister);

    // Close modal when clicking outside
    window.addEventListener('click', function (event) {
        const modals = ['loginModal', 'registerModal'];
        modals.forEach(modalId => {
            const modal = document.getElementById(modalId);
            if (event.target === modal) {
                hideModal(modalId);
            }
        });
    });
});

let selectedImageBase64 = null;

function resetChat() {
    document.getElementById('landingView').style.display = 'flex';
    document.getElementById('chatStream').style.display = 'none';
    document.getElementById('chatStream').innerHTML = '';
    selectedImageBase64 = null;
    document.getElementById('imageInput').value = '';
    document.getElementById('imagePreviewContainer').style.display = 'none';
}

function switchToChatMode() {
    document.getElementById('landingView').style.display = 'none';
    document.getElementById('chatStream').style.display = 'block';
}

async function checkStatus() {
    try {
        await fetch(`${API_BASE}/status`);
    } catch (error) {
        console.error('Status check failed:', error);
    }
}

async function checkAuthStatus() {
    const token = localStorage.getItem('access_token');
    if (!token) {
        showAuthButtons();
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.ok) {
            const user = await response.json();
            showUserInfo(user);
        } else {
            localStorage.removeItem('access_token');
            showAuthButtons();
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        showAuthButtons();
    }
}

async function handleQuery(e) {
    if (e) e.preventDefault();

    const queryInput = document.getElementById('queryInput');
    const kInput = document.getElementById('kInput');
    const generateAnswer = document.getElementById('generateAnswer');
    const submitBtn = document.getElementById('submitBtn');
    const imagePreviewContainer = document.getElementById('imagePreviewContainer');

    const query = queryInput.value.trim();
    if (!query && !selectedImageBase64) return;

    // Switch UI to chat mode
    switchToChatMode();

    // Append User Message
    appendUserMessage(query, selectedImageBase64);

    // Capture image before clearing
    const imageToSend = selectedImageBase64;

    // Clear input and reset height
    queryInput.value = '';
    queryInput.style.height = 'auto';
    selectedImageBase64 = null;
    document.getElementById('imageInput').value = '';
    imagePreviewContainer.style.display = 'none';
    submitBtn.disabled = true;

    // Show Loading
    const loadingId = appendLoadingMessage();

    try {
        const response = await fetch(`${API_BASE}/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: query || "Describe this image", // Fallback if only image sent
                k: parseInt(kInput.value),
                generate_answer: generateAnswer.checked,
                max_ctx: 4000,
                image: imageToSend
            })
        });

        const data = await response.json();

        // Remove loading message
        removeMessage(loadingId);

        if (response.ok) {
            appendAIMessage(data);
            loadChatHistory();
        } else {
            appendErrorMessage(data.error || 'Query failed');
        }
    } catch (error) {
        removeMessage(loadingId);
        appendErrorMessage(`Request failed: ${error.message}`);
    }
}

function appendUserMessage(text, imageBase64) {
    const chatStream = document.getElementById('chatStream');
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message user-message';

    let content = '';
    if (imageBase64) {
        content += `<img src="data:image/jpeg;base64,${imageBase64}" class="message-image">`;
    }
    if (text) {
        content += `<p>${escapeHtml(text)}</p>`;
    }

    msgDiv.innerHTML = `
        <div class="message-content">${content}</div>
    `;
    chatStream.appendChild(msgDiv);
    chatStream.scrollTop = chatStream.scrollHeight;
}

function appendLoadingMessage() {
    const chatStream = document.getElementById('chatStream');
    const msgDiv = document.createElement('div');
    const id = 'loading-' + Date.now();
    msgDiv.id = id;
    msgDiv.className = 'message ai-message';
    msgDiv.innerHTML = `
        <div class="message-avatar"><i class="fa-solid fa-bolt"></i></div>
        <div class="message-content">
            <p><i class="fa-solid fa-circle-notch fa-spin"></i></p>
        </div>
    `;
    chatStream.appendChild(msgDiv);
    chatStream.scrollTop = chatStream.scrollHeight;
    return id;
}

function removeMessage(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function appendAIMessage(data) {
    const chatStream = document.getElementById('chatStream');
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message ai-message';

    let content = '';
    if (data.answer) {
        content += `<p>${escapeHtml(data.answer)}</p>`;
    } else {
        content += `<p>No answer generated.</p>`;
    }

    // Sources Accordion (Styled minimally)
    if (data.chunks && data.chunks.length > 0) {
        const sourcesHtml = data.chunks.map(chunk => `
            <div style="margin-bottom: 0.5rem; padding: 0.5rem; background: rgba(255,255,255,0.05); border-radius: 4px;">
                <div style="font-weight: 600; font-size: 0.8rem; color: #b4b4b4;">${escapeHtml(chunk.title)}</div>
                <div style="font-size: 0.8rem; color: #b4b4b4;">${escapeHtml(chunk.chunk)}</div>
            </div>
        `).join('');

        content += `
            <div style="margin-top: 1rem;">
                <button onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'block' ? 'none' : 'block'" style="background: none; border: none; color: #b4b4b4; cursor: pointer; font-size: 0.8rem;">
                    <i class="fa-solid fa-book"></i> ${data.chunks.length} Sources
                </button>
                <div style="display: none; margin-top: 0.5rem;">
                    ${sourcesHtml}
                </div>
            </div>
        `;
    }

    msgDiv.innerHTML = `
        <div class="message-avatar"><i class="fa-solid fa-bolt"></i></div>
        <div class="message-content">${content}</div>
    `;
    chatStream.appendChild(msgDiv);
    chatStream.scrollTop = chatStream.scrollHeight;
}

function appendErrorMessage(text) {
    const chatStream = document.getElementById('chatStream');
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message ai-message';
    msgDiv.innerHTML = `
        <div class="message-avatar" style="border-color: var(--error-color); color: var(--error-color)"><i class="fa-solid fa-triangle-exclamation"></i></div>
        <div class="message-content"><p style="color: var(--error-color)">${escapeHtml(text)}</p></div>
    `;
    chatStream.appendChild(msgDiv);
    chatStream.scrollTop = chatStream.scrollHeight;
}

async function loadChatHistory() {
    const historyList = document.getElementById('chatHistoryList');
    // Clear existing items but keep title
    historyList.innerHTML = '<div class="section-title">Your chats</div>';

    try {
        const token = localStorage.getItem('access_token');
        if (!token) return;

        const response = await fetch(`${API_BASE}/chat-history`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.ok) {
            const data = await response.json();
            if (data.chats && data.chats.length > 0) {
                data.chats.forEach(chat => {
                    const btn = document.createElement('button');
                    btn.className = 'nav-item';
                    btn.innerHTML = `<span>${escapeHtml(chat.query)}</span>`;
                    historyList.appendChild(btn);
                });
            }
        }
    } catch (error) {
        console.error('Failed to load history:', error);
    }
}

function showUserInfo(user) {
    if (user && user.username) {
        document.getElementById('usernameDisplay').textContent = user.username;
        document.getElementById('userProfileSection').style.display = 'flex';
        document.getElementById('authButtons').style.display = 'none';

        // Initials
        const initials = user.username.substring(0, 2).toUpperCase();
        document.querySelector('.user-avatar').textContent = initials;
    }
}

function showAuthButtons() {
    document.getElementById('userProfileSection').style.display = 'none';
    document.getElementById('authButtons').style.display = 'block';
}

async function handleLogin(e) {
    e.preventDefault();
    const form = e.target;
    const username = form.loginUsername.value.trim();
    const password = form.loginPassword.value;
    const errorDiv = document.getElementById('loginError');
    errorDiv.style.display = 'none';

    try {
        const response = await fetch(`${API_BASE}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await response.json();

        if (response.ok) {
            if (data.access_token) localStorage.setItem('access_token', data.access_token);
            hideModal('loginModal');
            if (data.user) showUserInfo(data.user);
            form.reset();
            loadChatHistory();
        } else {
            errorDiv.textContent = data.detail || 'Login failed';
            errorDiv.style.display = 'block';
        }
    } catch (error) {
        errorDiv.textContent = 'Login failed: ' + error.message;
        errorDiv.style.display = 'block';
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const form = e.target;
    const username = form.registerUsername.value.trim();
    const email = form.registerEmail.value.trim();
    const password = form.registerPassword.value;
    const errorDiv = document.getElementById('registerError');
    errorDiv.style.display = 'none';

    try {
        const response = await fetch(`${API_BASE}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password })
        });
        const data = await response.json();

        if (response.ok) {
            const loginResp = await fetch(`${API_BASE}/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            if (loginResp.ok) {
                const loginData = await loginResp.json();
                localStorage.setItem('access_token', loginData.access_token);
                hideModal('registerModal');
                showUserInfo(loginData.user);
                loadChatHistory();
            }
        } else {
            errorDiv.textContent = data.detail || 'Registration failed';
            errorDiv.style.display = 'block';
        }
    } catch (error) {
        errorDiv.textContent = 'Error: ' + error.message;
        errorDiv.style.display = 'block';
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showModal(modalId) {
    document.getElementById(modalId).style.display = 'block';
}

function hideModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}