/**
 * FocusFlow - FocusBot AI Assistant Logic
 */

class FocusBotAssistant {
    constructor() {
        this.popup = null;
        this.body = null;
        this.isOpen = false;
        this.currentMode = 'menu'; // menu, chat, summary
        this.isTyping = false;
        
        this.init();
    }

    init() {
        const botEl = document.getElementById('focusBot');
        if (!botEl) return;

        // Ensure bot is visible
        botEl.classList.remove('d-none');
        botEl.style.cursor = 'pointer';
        
        // Add click listener to the robot
        botEl.addEventListener('click', () => this.togglePopup());

        // Create the popup element
        this.createPopup();
    }

    createPopup() {
        const popup = document.createElement('div');
        popup.id = 'botAssistantPopup';
        popup.className = 'bot-assistant-popup hidden';
        popup.innerHTML = `
            <div class="bot-assistant-header">
                <div class="d-flex align-items-center gap-2">
                    <div class="avatar-circle" style="width: 30px; height: 30px; font-size: 0.8rem;">🤖</div>
                    <span class="fw-bold">FocusBot AI</span>
                </div>
                <button class="btn btn-sm text-white opacity-70 p-0" id="closeBotPopup">✕</button>
            </div>
            <div class="bot-assistant-body" id="botAssistantBody">
                <!-- Menu or Messages Content -->
            </div>
            <div class="bot-assistant-footer hidden" id="botAssistantFooter">
                <input type="file" id="botPDFInput" class="hidden" accept="application/pdf">
                <div class="input-group input-group-sm">
                    <input type="text" id="botChatInput" class="form-control bg-secondary text-light border-0" placeholder="Ask me anything...">
                    <button class="btn btn-primary" id="botSendBtn">Send</button>
                </div>
            </div>
        `;
        document.body.appendChild(popup);
        this.popup = popup;
        this.body = document.getElementById('botAssistantBody');
        this.footer = document.getElementById('botAssistantFooter');

        // Close button
        document.getElementById('closeBotPopup').addEventListener('click', () => this.togglePopup(false));

        // Send message
        document.getElementById('botSendBtn').addEventListener('click', () => this.handleSendMessage());
        document.getElementById('botChatInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.handleSendMessage();
        });

        // PDF Upload listener
        document.getElementById('botPDFInput').addEventListener('change', (e) => this.handlePDFUpload(e));

        this.showMenu();
    }

    togglePopup(forceState) {
        this.isOpen = forceState !== undefined ? forceState : !this.isOpen;
        this.popup.classList.toggle('hidden', !this.isOpen);
        
        if (this.isOpen) {
            this.showMenu();
        }
    }

    showMenu() {
        this.currentMode = 'menu';
        this.footer.classList.add('hidden');
        this.body.innerHTML = `
            <div class="text-center mb-4">
                <h5 class="text-white mb-2">Hello! I'm your study assistant.</h5>
                <p class="small text-muted">How can I help you today?</p>
            </div>
            <button class="bot-menu-item" onclick="botAssistant.startChat()">
                <span>💬</span>
                <span>Chat with me</span>
            </button>
            <button class="bot-menu-item" onclick="botAssistant.summarizePDF()">
                <span>📄</span>
                <span>Summarize the PDF</span>
            </button>
            <button class="bot-menu-item" onclick="botAssistant.summarizeYouTube()">
                <span>📺</span>
                <span>Summarize the YT vid</span>
            </button>
        `;
    }

    startChat() {
        this.currentMode = 'chat';
        this.body.innerHTML = '';
        this.footer.classList.remove('hidden');
        this.addMessage('bot', "Sure! I'm here to help. What's on your mind?");
        document.getElementById('botChatInput').focus();
    }

    addMessage(role, text) {
        const msg = document.createElement('div');
        msg.className = `msg-bubble msg-${role}`;
        msg.textContent = text;
        this.body.appendChild(msg);
        this.body.scrollTop = this.body.scrollHeight;
    }

    showTyping(show) {
        let indicator = document.getElementById('typingIndicator');
        if (show) {
            if (!indicator) {
                indicator = document.createElement('div');
                indicator.id = 'typingIndicator';
                indicator.className = 'typing-indicator';
                indicator.textContent = 'FocusBot is thinking...';
                this.body.appendChild(indicator);
            }
        } else if (indicator) {
            indicator.remove();
        }
        this.body.scrollTop = this.body.scrollHeight;
    }

    async handleSendMessage() {
        const input = document.getElementById('botChatInput');
        const text = input.value.trim();
        if (!text || this.isTyping) return;

        input.value = '';
        this.addMessage('user', text);
        this.isTyping = true;
        this.showTyping(true);

        try {
            const res = await authenticatedFetch(`${API_URL}/api/ai/chat`, {
                method: 'POST',
                body: JSON.stringify({ message: text })
            });

            if (!res.ok) throw new Error("Connection failed");
            const data = await res.json();
            
            this.showTyping(false);
            this.addMessage('bot', data.message);
        } catch (e) {
            this.showTyping(false);
            this.addMessage('bot', "Sorry, I had trouble connecting to my brain. Please try again later!");
        } finally {
            this.isTyping = false;
        }
    }

    async summarizePDF() {
        // If we are on study page with active PDF, use it.
        if (typeof sessionPDFs !== 'undefined' && sessionPDFs.length > 0) {
            this.summarizeActiveStudyPDF();
        } else {
            // Otherwise, prompt for upload
            document.getElementById('botPDFInput').click();
        }
    }

    async summarizeActiveStudyPDF() {
        this.currentMode = 'summary';
        this.body.innerHTML = `<div class="text-center py-4"><span class="spinner-border text-primary"></span><p class="mt-2 small">Reading your session notes...</p></div>`;
        this.footer.classList.remove('hidden');

        try {
            const pdfName = sessionPDFs[activePDFIndex >= 0 ? activePDFIndex : 0].name;
            const res = await authenticatedFetch(`${API_URL}/api/ai/summarize_pdf`, {
                method: 'POST',
                body: JSON.stringify({ text: `Context: Active study file. Name: ${pdfName}` })
            });

            const data = await res.json();
            this.body.innerHTML = '';
            this.addMessage('bot', `Here's a summary of the active PDF (${pdfName}):`);
            this.addMessage('bot', data.summary);
        } catch (e) {
            this.addMessage('bot', "Could not summarize session PDF.");
        }
    }

    async handlePDFUpload(e) {
        const file = e.target.files[0];
        if (!file || file.type !== 'application/pdf') return;

        this.currentMode = 'summary';
        this.body.innerHTML = `<div class="text-center py-4"><span class="spinner-border text-primary"></span><p class="mt-2 small">Uploading & Summarizing ${file.name}...</p></div>`;
        this.footer.classList.remove('hidden');

        const formData = new FormData();
        formData.append('file', file);

        try {
            const token = getToken();
            const res = await fetch(`${API_URL}/api/ai/summarize_upload`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
                body: formData
            });

            if (!res.ok) throw new Error("Upload failed");

            const data = await res.json();
            this.body.innerHTML = '';
            this.addMessage('bot', `I've analyzed ${file.name}:`);
            this.addMessage('bot', data.summary);
        } catch (err) {
            this.body.innerHTML = '';
            this.addMessage('bot', "Sorry, I couldn't process that PDF. Make sure it's text-based and not too large.");
        } finally {
            e.target.value = ''; // Reset input
        }
    }

    async summarizeYouTube() {
        const iframe = document.getElementById('youtubeEmbedFrame');
        if (!iframe || !iframe.src) {
            this.startChat();
            this.addMessage('bot', "Please load a YouTube video in the Study Tools panel first!");
            return;
        }

        this.currentMode = 'summary';
        this.body.innerHTML = `<div class="text-center py-4"><span class="spinner-border text-primary"></span><p class="mt-2 small">Analyzing video...</p></div>`;
        this.footer.classList.remove('hidden');

        try {
            const res = await authenticatedFetch(`${API_URL}/api/ai/summarize_yt`, {
                method: 'POST',
                body: JSON.stringify({ title: "Study Video", url: iframe.src })
            });

            const data = await res.json();
            this.body.innerHTML = '';
            this.addMessage('bot', "I've analyzed the video for you:");
            this.addMessage('bot', data.summary);
        } catch (e) {
            this.body.innerHTML = '';
            this.addMessage('bot', "Couldn't summarize the video right now. Is it allowed to be summarized?");
        }
    }
}

// Global instance
let botAssistant;
document.addEventListener('DOMContentLoaded', () => {
    botAssistant = new FocusBotAssistant();
});
