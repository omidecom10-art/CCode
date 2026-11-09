let currentChannel = null;

function initChat(channel) {
    currentChannel = channel;
    loadHistory();
    loadConversations();
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
            messages.forEach(m => appendMessage(m.role, m.content));
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

function appendMessage(role, content) {
    const welcome = document.getElementById('chatWelcome');
    if (welcome) welcome.remove();

    const container = document.getElementById('chatMessages');
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble chat-bubble-' + role;

    if (role === 'assistant') {
        bubble.innerHTML = renderMarkdown(content);
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
