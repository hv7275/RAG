// RAG System Frontend JavaScript
const API_BASE = '';

// Check authentication status on page load
document.addEventListener('DOMContentLoaded', function() {
    checkStatus();
    checkAuthStatus();
    
    // Query form submission
    document.getElementById('queryForm').addEventListener('submit', handleQuery);
    
    // Rebuild button
    document.getElementById('rebuildBtn').addEventListener('click', handleRebuild);
    
    // Copy answer button
    document.getElementById('copyAnswerBtn').addEventListener('click', copyAnswer);
    
    // Authentication buttons
    document.getElementById('loginBtn').addEventListener('click', () => showModal('loginModal'));
    document.getElementById('registerBtn').addEventListener('click', () => showModal('registerModal'));
    document.getElementById('logoutBtn').addEventListener('click', handleLogout);
    document.getElementById('chatHistoryBtn').addEventListener('click', () => {
        showModal('chatHistoryModal');
        loadChatHistory();
    });
    
    // Modal close buttons
    document.getElementById('closeLoginModal').addEventListener('click', () => hideModal('loginModal'));
    document.getElementById('closeRegisterModal').addEventListener('click', () => hideModal('registerModal'));
    document.getElementById('closeChatHistoryModal').addEventListener('click', () => hideModal('chatHistoryModal'));
    
    // Login form
    document.getElementById('loginForm').addEventListener('submit', handleLogin);
    
    // Register form
    document.getElementById('registerForm').addEventListener('submit', handleRegister);
    
    // Close modal when clicking outside
    window.addEventListener('click', function(event) {
        const modals = ['loginModal', 'registerModal', 'chatHistoryModal'];
        modals.forEach(modalId => {
            const modal = document.getElementById(modalId);
            if (event.target === modal) {
                hideModal(modalId);
            }
        });
    });
});

async function checkStatus() {
    try {
        const response = await fetch(`${API_BASE}/status`);
        const data = await response.json();
        
        if (data.embeddings_loaded || data.index_exists) {
            document.getElementById('statusValue').textContent = 'Ready';
            document.getElementById('statusValue').style.color = '#28a745';
            document.getElementById('chunkCount').textContent = data.total_chunks || 0;
        } else {
            document.getElementById('statusValue').textContent = 'Not Ready';
            document.getElementById('statusValue').style.color = '#dc3545';
            document.getElementById('chunkCount').textContent = '0';
        }
    } catch (error) {
        document.getElementById('statusValue').textContent = 'Error';
        document.getElementById('statusValue').style.color = '#dc3545';
        console.error('Status check failed:', error);
    }
}

async function handleQuery(e) {
    e.preventDefault();
    
    const queryInput = document.getElementById('queryInput');
    const kInput = document.getElementById('kInput');
    const generateAnswer = document.getElementById('generateAnswer');
    const submitBtn = document.getElementById('submitBtn');
    const resultsSection = document.getElementById('resultsSection');
    const errorSection = document.getElementById('errorSection');
    
    const query = queryInput.value.trim();
    if (!query) {
        showError('Please enter a query');
        return;
    }
    
    // Show loading state
    submitBtn.disabled = true;
    submitBtn.querySelector('.btn-text').style.display = 'none';
    submitBtn.querySelector('.btn-loader').style.display = 'inline';
    resultsSection.style.display = 'none';
    errorSection.style.display = 'none';
    
    try {
        const response = await fetch(`${API_BASE}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                k: parseInt(kInput.value),
                generate_answer: generateAnswer.checked,
                max_ctx: 4000
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            displayResults(data);
        } else {
            showError(data.error || 'Query failed');
        }
    } catch (error) {
        showError(`Request failed: ${error.message}`);
    } finally {
        // Reset button state
        submitBtn.disabled = false;
        submitBtn.querySelector('.btn-text').style.display = 'inline';
        submitBtn.querySelector('.btn-loader').style.display = 'none';
    }
}

function displayResults(data) {
    const resultsSection = document.getElementById('resultsSection');
    const answerSection = document.getElementById('answerSection');
    const answerContent = document.getElementById('answerContent');
    const chunksList = document.getElementById('chunksList');
    const errorSection = document.getElementById('errorSection');
    
    // Hide error section
    errorSection.style.display = 'none';
    
    // Display answer if available
    if (data.answer && data.answer.trim() !== '') {
        answerContent.textContent = data.answer;
        answerSection.style.display = 'block';
    } else {
        answerSection.style.display = 'none';
    }
    
    // Display chunks
    if (data.chunks && data.chunks.length > 0) {
        chunksList.innerHTML = data.chunks.map((chunk, index) => `
            <div class="chunk-card">
                <div class="chunk-header">
                    <div class="chunk-title">${escapeHtml(chunk.title)}</div>
                    <div class="chunk-header-right">
                        <div class="chunk-meta">
                            ${chunk.start ? `<span>Start: ${escapeHtml(chunk.start)}</span>` : ''}
                            ${chunk.end ? `<span>End: ${escapeHtml(chunk.end)}</span>` : ''}
                            <span class="chunk-score">Score: ${chunk.score.toFixed(3)}</span>
                        </div>
                        <button class="copy-chunk-btn" data-chunk-index="${index}" title="Copy this chunk to clipboard">
                            <span class="copy-icon">📋</span>
                            <span class="copy-text">Copy</span>
                        </button>
                    </div>
                </div>
                <div class="chunk-text" data-chunk-content="${index}">${escapeHtml(chunk.chunk)}</div>
            </div>
        `).join('');
        
        // Add event listeners for chunk copy buttons
        chunksList.querySelectorAll('.copy-chunk-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const chunkIndex = this.getAttribute('data-chunk-index');
                const chunkContent = chunksList.querySelector(`[data-chunk-content="${chunkIndex}"]`);
                copyChunkText(chunkContent.textContent, this);
            });
        });
    } else {
        chunksList.innerHTML = '<p>No chunks found.</p>';
    }
    
    // Show results section
    resultsSection.style.display = 'block';
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function showError(message) {
    const errorSection = document.getElementById('errorSection');
    const errorMessage = document.getElementById('errorMessage');
    const resultsSection = document.getElementById('resultsSection');
    
    errorMessage.textContent = message;
    errorSection.style.display = 'block';
    resultsSection.style.display = 'none';
    errorSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function handleRebuild() {
    const rebuildBtn = document.getElementById('rebuildBtn');
    const originalText = rebuildBtn.textContent;
    
    if (!confirm('Are you sure you want to rebuild the index? This may take a while.')) {
        return;
    }
    
    rebuildBtn.disabled = true;
    rebuildBtn.textContent = 'Rebuilding...';
    
    try {
        const response = await fetch(`${API_BASE}/rebuild`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert(`Index rebuilt successfully! Total chunks: ${data.total_chunks}`);
            checkStatus();
        } else {
            alert(`Rebuild failed: ${data.error || 'Unknown error'}`);
        }
    } catch (error) {
        alert(`Rebuild failed: ${error.message}`);
    } finally {
        rebuildBtn.disabled = false;
        rebuildBtn.textContent = originalText;
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function copyTextToClipboard(text) {
    // Use the Clipboard API if available
    if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
    } else {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        document.execCommand('copy');
        textArea.remove();
    }
}

async function copyAnswer() {
    const answerContent = document.getElementById('answerContent');
    const copyBtn = document.getElementById('copyAnswerBtn');
    const copyText = copyBtn.querySelector('.copy-text');
    
    const answerText = answerContent.textContent || answerContent.innerText;
    
    if (!answerText || answerText.trim() === '') {
        return;
    }
    
    try {
        await copyTextToClipboard(answerText);
        
        // Visual feedback
        copyBtn.classList.add('copied');
        const originalText = copyText.textContent;
        copyText.textContent = 'Copied';
        
        setTimeout(() => {
            copyBtn.classList.remove('copied');
            copyText.textContent = originalText;
        }, 2000);
        
    } catch (error) {
        console.error('Failed to copy text:', error);
        alert('Failed to copy answer to clipboard. Please select and copy manually.');
    }
}

async function copyChunkText(chunkText, copyBtn) {
    if (!chunkText || chunkText.trim() === '') {
        return;
    }
    
    try {
        await copyTextToClipboard(chunkText);
        
        // Visual feedback
        const copyText = copyBtn.querySelector('.copy-text');
        copyBtn.classList.add('copied');
        const originalText = copyText.textContent;
        copyText.textContent = 'Copied';
        
        setTimeout(() => {
            copyBtn.classList.remove('copied');
            copyText.textContent = originalText;
        }, 2000);
        
    } catch (error) {
        console.error('Failed to copy chunk text:', error);
        alert('Failed to copy chunk to clipboard. Please select and copy manually.');
    }
}

// Authentication functions
async function checkAuthStatus() {
    try {
        const token = localStorage.getItem('access_token');
        if (!token) {
            showAuthButtons();
            return;
        }
        
        const response = await fetch(`${API_BASE}/me`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        if (response.ok) {
            const user = await response.json();
            showUserInfo(user);
        } else {
            // Token invalid, clear it
            localStorage.removeItem('access_token');
            showAuthButtons();
        }
    } catch (error) {
        showAuthButtons();
    }
}

function showUserInfo(user) {
    if (user && user.username) {
        document.getElementById('usernameDisplay').textContent = `Hello, ${user.username}`;
        document.getElementById('userInfo').style.display = 'flex';
        document.getElementById('authButtons').style.display = 'none';
        // Store token if provided
        if (user.token) {
            localStorage.setItem('access_token', user.token);
        }
    }
}

function showAuthButtons() {
    document.getElementById('userInfo').style.display = 'none';
    document.getElementById('authButtons').style.display = 'flex';
}

async function handleLogin(e) {
    e.preventDefault();
    const form = e.target;
    const username = form.loginUsername.value.trim();
    const password = form.loginPassword.value;
    const errorDiv = document.getElementById('loginError');
    
    // Clear previous errors
    errorDiv.style.display = 'none';
    errorDiv.textContent = '';
    
    // Basic validation
    if (!username || !password) {
        errorDiv.textContent = 'Please enter both username and password';
        errorDiv.style.display = 'block';
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password })
        });
        
        let data;
        try {
            data = await response.json();
        } catch (e) {
            data = { detail: response.statusText || 'Login failed' };
        }
        
        if (response.ok) {
            // Store token if provided
            if (data.access_token) {
                localStorage.setItem('access_token', data.access_token);
            }
            // Store user info
            if (data.user) {
                hideModal('loginModal');
                showUserInfo(data.user);
                form.reset();
                errorDiv.style.display = 'none';
            } else {
                errorDiv.textContent = 'Login successful but user data not received';
                errorDiv.style.display = 'block';
            }
        } else {
            // Show detailed error message
            const errorMsg = data.detail || data.error || `Login failed (${response.status})`;
            errorDiv.textContent = errorMsg;
            errorDiv.style.display = 'block';
            console.error('Login error:', data);
        }
    } catch (error) {
        errorDiv.textContent = 'Login failed: ' + error.message + '. Please check if the API server is running.';
        errorDiv.style.display = 'block';
        console.error('Login exception:', error);
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const form = e.target;
    const username = form.registerUsername.value.trim();
    const email = form.registerEmail.value.trim();
    const password = form.registerPassword.value;
    const errorDiv = document.getElementById('registerError');
    
    // Clear previous errors
    errorDiv.style.display = 'none';
    errorDiv.textContent = '';
    
    // Basic validation
    if (!username || !email || !password) {
        errorDiv.textContent = 'Please fill in all fields';
        errorDiv.style.display = 'block';
        return;
    }
    
    if (password.length < 6) {
        errorDiv.textContent = 'Password must be at least 6 characters long';
        errorDiv.style.display = 'block';
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, email, password })
        });
        
        let data;
        try {
            data = await response.json();
        } catch (e) {
            data = { detail: response.statusText || 'Registration failed' };
        }
        
        if (response.ok) {
            // Auto login after registration
            const loginResponse = await fetch(`${API_BASE}/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username, password })
            });
            
            if (loginResponse.ok) {
                const loginData = await loginResponse.json();
                // Store token if provided
                if (loginData.access_token) {
                    localStorage.setItem('access_token', loginData.access_token);
                }
                hideModal('registerModal');
                if (loginData.user) {
                    showUserInfo(loginData.user);
                } else {
                    showUserInfo({ username: username, token: loginData.access_token });
                }
                form.reset();
                errorDiv.style.display = 'none';
            } else {
                // Registration succeeded but login failed
                errorDiv.textContent = 'Registration successful, but login failed. Please try logging in manually.';
                errorDiv.style.display = 'block';
            }
        } else {
            // Show detailed error message
            const errorMsg = data.detail || data.error || `Registration failed (${response.status})`;
            errorDiv.textContent = errorMsg;
            errorDiv.style.display = 'block';
            console.error('Registration error:', data);
        }
    } catch (error) {
        errorDiv.textContent = 'Registration failed: ' + error.message + '. Please check if the API server is running.';
        errorDiv.style.display = 'block';
        console.error('Registration exception:', error);
    }
}

async function handleLogout() {
    try {
        await fetch(`${API_BASE}/logout`, {
            method: 'POST'
        });
        // Clear token from localStorage
        localStorage.removeItem('access_token');
        showAuthButtons();
    } catch (error) {
        console.error('Logout failed:', error);
        // Clear token anyway
        localStorage.removeItem('access_token');
        showAuthButtons();
    }
}

async function loadChatHistory() {
    const chatHistoryList = document.getElementById('chatHistoryList');
    chatHistoryList.innerHTML = '<p>Loading chat history...</p>';
    
    try {
        const token = localStorage.getItem('access_token');
        if (!token) {
            chatHistoryList.innerHTML = '<p>Please login to view chat history.</p>';
            return;
        }
        
        const response = await fetch(`${API_BASE}/chat-history`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        if (response.ok) {
            const data = await response.json();
            if (data.chats && data.chats.length > 0) {
                chatHistoryList.innerHTML = data.chats.map(chat => `
                    <div class="chat-history-item">
                        <div class="chat-history-item-header">
                            <div class="chat-history-item-date">${new Date(chat.created_at).toLocaleString()}</div>
                        </div>
                        <div class="chat-history-item-query">${escapeHtml(chat.query)}</div>
                        <div class="chat-history-item-answer">${escapeHtml(chat.answer || 'No answer generated')}</div>
                    </div>
                `).join('');
            } else {
                chatHistoryList.innerHTML = '<p>No chat history found.</p>';
            }
        } else {
            chatHistoryList.innerHTML = '<p>Failed to load chat history. Please login again.</p>';
        }
    } catch (error) {
        chatHistoryList.innerHTML = '<p>Error loading chat history: ' + error.message + '</p>';
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