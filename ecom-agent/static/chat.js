let currentChannel = null;
let voiceMode = false;
let recognition = null;
let isListening = false;
let synth = window.speechSynthesis;
let svVoice = null;

function initChat(channel) {
    currentChannel = channel;
    loadHistory();
    loadConversations();
    initVoice();
}

function initVoice() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition || !synth) {
        document.getElementById('voiceUnsupported').style.display = 'inline';
        document.getElementById('voiceToggle').style.display = 'none';
        document.getElementById('micBtn').style.display = 'none';
        return;
    }

    recognition = new SpeechRecognition();
    recognition.lang = 'sv-SE';
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onresult = function(e) {
        const text = e.results[0][0].transcript;
        document.getElementById('chatInput').value = text;
        stopListening();
        sendMessage();
    };

    recognition.onerror = function(e) {
        stopListening();
        if (e.error !== 'no-speech' && e.error !== 'aborted') {
            console.warn('Speech error:', e.error);
        }
    };

    recognition.onend = function() {
        stopListening();
    };

    pickSwedishVoice();
    synth.onvoiceschanged = pickSwedishVoice;
}

function pickSwedishVoice() {
    const voices = synth.getVoices();
    svVoice = voices.find(v => v.lang === 'sv-SE')
        || voices.find(v => v.lang.startsWith('sv'))
        || null;
}

function toggleVoiceMode(on) {
    voiceMode = on;
    if (!on && synth.speaking) synth.cancel();
}

function toggleMic() {
    if (!recognition) return;
    if (isListening) {
        recognition.abort();
        stopListening();
    } else {
        startListening();
    }
}

function startListening() {
    if (!recognition) return;
    isListening = true;
    const btn = document.getElementById('micBtn');
    btn.classList.add('listening');
    try { recognition.start(); } catch (e) {}
}

function stopListening() {
    isListening = false;
    const btn = document.getElementById('micBtn');
    if (btn) btn.classList.remove('listening');
}

function speakText(text) {
    if (!synth) return;
    synth.cancel();
    const clean = text.replace(/```[\s\S]*?```/g, '')
        .replace(/`[^`]+`/g, '')
        .replace(/\*\*(.+?)\*\*/g, '$1')
        .replace(/\*(.+?)\*/g, '$1')
        .replace(/^#{1,4}\s+/gm, '')
        .replace(/\|[^|]+\|/g, '')
        .replace(/[-]+/g, ' ')
        .replace(/\n/g, '. ')
        .replace(/\s+/g, ' ')
        .trim();
    if (!clean) return;

    const maxLen = 200;
    const chunks = [];
    let remaining = clean;
    while (remaining.length > 0) {
        if (remaining.length <= maxLen) {
            chunks.push(remaining);
            break;
        }
        let cut = remaining.lastIndexOf('. ', maxLen);
        if (cut === -1 || cut < 50) cut = remaining.lastIndexOf(' ', maxLen);
        if (cut === -1) cut = maxLen;
        chunks.push(remaining.slice(0, cut + 1));
        remaining = remaining.slice(cut + 1);
    }

    chunks.forEach(chunk => {
        const utter = new SpeechSynthesisUtterance(chunk);
        utter.lang = 'sv-SE';
        if (svVoice) utter.voice = svVoice;
        utter.rate = 1;
        synth.speak(utter);
    });
}

function switchChannel(val) {
    currentChannel = val === 'null' ? null : parseInt(val, 10);
    document.getElementById('chatMessages').innerHTML =
        '<div class="chat-welcome" id="chatWelcome">' +
        '<div class="chat-welcome-icon">&#129302;</div>' +
        '<h2>Hej! Jag är din e-handelsassistent.</h2>' +
        '<p>Ställ en fråga om din butik, försäljning, marknadsföring eller något annat.</p></div>';
    updateTitle();
    loadHistory();
    loadConversations();
}

function updateTitle() {
    const sel = document.getElementById('channelSelect');
    const title = sel.options[sel.selectedIndex].textContent.trim();
    document.getElementById('chatTitle').textContent = title;
}

function loadHistory() {
    const storeParam = currentChannel === null ? 'null' : currentChannel;
    fetch('/api/chat/history/' + storeParam)
        .then(r => r.json())
        .then(messages => {
            const container = document.getElementById('chatMessages');
            container.innerHTML = '';
            if (messages.length === 0) {
                container.innerHTML =
                    '<div class="chat-welcome" id="chatWelcome">' +
                    '<div class="chat-welcome-icon">&#129302;</div>' +
                    '<h2>Hej! Jag är din e-handelsassistent.</h2>' +
                    '<p>Ställ en fråga om din butik, försäljning, marknadsföring eller något annat.</p></div>';
                document.getElementById('chatMsgCount').textContent = '';
                return;
            }
            messages.forEach(m => appendMessage(m.role, m.content, false));
            document.getElementById('chatMsgCount').textContent = messages.length + ' meddelanden';
            scrollToBottom();
        });
}

function loadConversations() {
    fetch('/api/chat/conversations')
        .then(r => r.json())
        .then(convos => {
            const list = document.getElementById('chatHistoryList');
            if (convos.length === 0) {
                list.innerHTML = '<p class="muted" style="padding:12px;font-size:13px;">Inga konversationer ännu.</p>';
                return;
            }
            let html = '';
            convos.forEach(c => {
                const name = c.store_name || 'Generell';
                const active = (c.store_id === null && currentChannel === null) ||
                    c.store_id === currentChannel;
                const date = c.last_at ? c.last_at.slice(0, 16).replace('T', ' ') : '';
                html += '<div class="chat-history-item' + (active ? ' active' : '') + '" ' +
                    'onclick="selectConversation(' + (c.store_id === null ? 'null' : c.store_id) + ')">' +
                    '<div class="chat-history-name">' + esc(name) + '</div>' +
                    '<div class="chat-history-meta">' +
                    '<span>' + c.msg_count + ' meddelanden</span>' +
                    '<span>' + esc(date) + '</span>' +
                    '</div></div>';
            });
            list.innerHTML = html;
        });
}

function selectConversation(storeId) {
    const sel = document.getElementById('channelSelect');
    sel.value = storeId === null ? 'null' : String(storeId);
    switchChannel(sel.value);
}

function newConversation() {
    const storeParam = currentChannel === null ? 'null' : currentChannel;
    fetch('/api/chat/clear/' + storeParam, { method: 'POST' })
        .then(() => {
            loadHistory();
            loadConversations();
        });
}

function sendMessage() {
    const input = document.getElementById('chatInput');
    const msg = input.value.trim();
    if (!msg) return;

    input.value = '';
    input.style.height = 'auto';
    appendMessage('user', msg);
    scrollToBottom();

    const sendBtn = document.getElementById('sendBtn');
    sendBtn.disabled = true;

    showTypingIndicator();

    fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            message: msg,
            store_id: currentChannel
        })
    })
        .then(r => r.json())
        .then(data => {
            removeTypingIndicator();
            sendBtn.disabled = false;
            if (data.error) {
                appendMessage('assistant', 'Fel: ' + data.error);
            } else {
                appendMessage('assistant', data.reply);
            }
            scrollToBottom();
            loadConversations();
        })
        .catch(err => {
            removeTypingIndicator();
            sendBtn.disabled = false;
            appendMessage('assistant', 'Något gick fel: ' + err.message);
            scrollToBottom();
        });
}

function appendMessage(role, content, autoSpeak) {
    const welcome = document.getElementById('chatWelcome');
    if (welcome) welcome.remove();

    const container = document.getElementById('chatMessages');
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble chat-bubble-' + role;

    if (role === 'assistant') {
        bubble.innerHTML = renderMarkdown(content);

        const speakerBtn = document.createElement('button');
        speakerBtn.className = 'bubble-speak-btn';
        speakerBtn.title = 'Läs upp';
        speakerBtn.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg>';
        speakerBtn.onclick = function() { speakText(content); };
        bubble.appendChild(speakerBtn);

        if (autoSpeak !== false && voiceMode && synth) {
            speakText(content);
        }
    } else {
        bubble.textContent = content;
    }

    container.appendChild(bubble);
}

function showTypingIndicator() {
    const container = document.getElementById('chatMessages');
    const el = document.createElement('div');
    el.className = 'chat-bubble chat-bubble-assistant chat-typing';
    el.id = 'typingIndicator';
    el.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
    container.appendChild(el);
    scrollToBottom();
}

function removeTypingIndicator() {
    const el = document.getElementById('typingIndicator');
    if (el) el.remove();
}

function scrollToBottom() {
    const container = document.getElementById('chatMessages');
    container.scrollTop = container.scrollHeight;
}

function handleChatKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

function autoGrow(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
}

function toggleChatSidebar() {
    document.getElementById('chatSidebar').classList.toggle('open');
}

function renderMarkdown(text) {
    let html = esc(text);

    // Code blocks
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, function (m, lang, code) {
        return '<pre class="md-code-block"><code>' + code.trim() + '</code></pre>';
    });

    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code class="md-inline-code">$1</code>');

    // Bold
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // Italic
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

    // Tables
    html = html.replace(/((?:\|.+\|\n?)+)/g, function (table) {
        const rows = table.trim().split('\n');
        if (rows.length < 2) return table;

        let out = '<table class="md-table">';
        const headerCells = rows[0].split('|').filter(c => c.trim());
        out += '<thead><tr>';
        headerCells.forEach(c => { out += '<th>' + c.trim() + '</th>'; });
        out += '</tr></thead><tbody>';

        for (let i = 2; i < rows.length; i++) {
            const cells = rows[i].split('|').filter(c => c.trim());
            if (cells.length === 0) continue;
            out += '<tr>';
            cells.forEach(c => { out += '<td>' + c.trim() + '</td>'; });
            out += '</tr>';
        }
        out += '</tbody></table>';
        return out;
    });

    // Unordered lists
    html = html.replace(/((?:^|\n)- .+(?:\n- .+)*)/g, function (block) {
        const items = block.trim().split('\n');
        let out = '<ul class="md-list">';
        items.forEach(item => {
            out += '<li>' + item.replace(/^- /, '') + '</li>';
        });
        out += '</ul>';
        return out;
    });

    // Ordered lists
    html = html.replace(/((?:^|\n)\d+\. .+(?:\n\d+\. .+)*)/g, function (block) {
        const items = block.trim().split('\n');
        let out = '<ol class="md-list">';
        items.forEach(item => {
            out += '<li>' + item.replace(/^\d+\. /, '') + '</li>';
        });
        out += '</ol>';
        return out;
    });

    // Headers
    html = html.replace(/^### (.+)$/gm, '<h4 class="md-heading">$1</h4>');
    html = html.replace(/^## (.+)$/gm, '<h3 class="md-heading">$1</h3>');
    html = html.replace(/^# (.+)$/gm, '<h2 class="md-heading">$1</h2>');

    // Line breaks
    html = html.replace(/\n/g, '<br>');

    return html;
}

function esc(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}
