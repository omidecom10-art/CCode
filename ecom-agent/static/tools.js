function initTools() {
    calcMargin();
    calcPricing();
}

/* ── Tab switching ── */

function switchTab(tab) {
    document.querySelectorAll('.tools-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tools-panel').forEach(p => p.classList.remove('active'));
    document.querySelector('[data-tab="' + tab + '"]').classList.add('active');
    document.getElementById('panel-' + tab).classList.add('active');
}

/* ── Margin calculator (pure JS, no API) ── */

function calcMargin() {
    const cost = parseFloat(document.getElementById('mcCost').value) || 0;
    const shipping = parseFloat(document.getElementById('mcShipping').value) || 0;
    const fee = parseFloat(document.getElementById('mcFee').value) || 0;
    const ad = parseFloat(document.getElementById('mcAd').value) || 0;
    const price = parseFloat(document.getElementById('mcPrice').value) || 0;

    if (price <= 0) {
        setMarginResults('—');
        return;
    }

    const shopifyFee = price * (fee / 100);
    const totalCost = cost + shipping + ad + shopifyFee;
    const grossProfit = price - (cost + shipping);
    const grossMargin = (grossProfit / price) * 100;
    const netProfit = price - totalCost;
    const netMargin = (netProfit / price) * 100;
    const breakEven = netProfit > 0 ? (ad / netProfit) : 0;
    const roi = totalCost > 0 ? (netProfit / totalCost) * 100 : 0;

    document.getElementById('resGrossMargin').textContent = fmt(grossMargin) + ' %';
    document.getElementById('resNetMargin').textContent = fmt(netMargin) + ' %';
    document.getElementById('resGrossProfit').textContent = fmt(grossProfit) + ' kr';
    document.getElementById('resNetProfit').textContent = fmt(netProfit) + ' kr';
    document.getElementById('resShopifyFee').textContent = fmt(shopifyFee) + ' kr';
    document.getElementById('resTotalCost').textContent = fmt(totalCost) + ' kr';
    document.getElementById('resBreakEven').textContent = breakEven > 0 ? Math.ceil(breakEven) + ' st' : '—';
    document.getElementById('resROI').textContent = fmt(roi) + ' %';

    colorMargin('resGrossMargin', grossMargin);
    colorMargin('resNetMargin', netMargin);
    colorProfit('resNetProfit', netProfit);
}

function setMarginResults(val) {
    ['resGrossMargin', 'resNetMargin', 'resGrossProfit', 'resNetProfit',
     'resShopifyFee', 'resTotalCost', 'resBreakEven', 'resROI'].forEach(id => {
        document.getElementById(id).textContent = val;
        document.getElementById(id).style.color = '';
    });
}

function colorMargin(id, val) {
    const el = document.getElementById(id);
    if (val >= 40) el.style.color = 'var(--success)';
    else if (val >= 20) el.style.color = '#f1c40f';
    else el.style.color = 'var(--danger)';
}

function colorProfit(id, val) {
    const el = document.getElementById(id);
    el.style.color = val >= 0 ? 'var(--success)' : 'var(--danger)';
}

/* ── Pricing helper (pure JS) ── */

function calcPricing() {
    const cost = parseFloat(document.getElementById('prCost').value) || 0;
    const shipping = parseFloat(document.getElementById('prShipping').value) || 0;
    const margin = parseFloat(document.getElementById('prMargin').value) || 0;

    if (margin <= 0 || margin >= 100) {
        document.getElementById('resSuggestedPrice').textContent = '—';
        document.getElementById('resProfitUnit').textContent = '—';
        document.getElementById('resPrTotalCost').textContent = '—';
        return;
    }

    const totalCost = cost + shipping;
    const suggestedPrice = totalCost / (1 - margin / 100);
    const profit = suggestedPrice - totalCost;

    document.getElementById('resSuggestedPrice').textContent = fmt(suggestedPrice) + ' kr';
    document.getElementById('resProfitUnit').textContent = fmt(profit) + ' kr';
    document.getElementById('resPrTotalCost').textContent = fmt(totalCost) + ' kr';
}

/* ── SWOT analysis (API call) ── */

function runSwot() {
    const input = document.getElementById('swotInput').value.trim();
    if (!input) { alert('Ange en beskrivning.'); return; }

    const btn = document.getElementById('swotBtn');
    btn.disabled = true;
    document.getElementById('swotLoading').style.display = 'flex';
    document.getElementById('swotResult').style.display = 'none';
    document.getElementById('swotError').style.display = 'none';

    fetch('/api/tools/swot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description: input })
    })
        .then(r => r.json())
        .then(data => {
            btn.disabled = false;
            document.getElementById('swotLoading').style.display = 'none';
            if (data.error) {
                document.getElementById('swotError').textContent = data.error;
                document.getElementById('swotError').style.display = 'block';
                return;
            }
            document.getElementById('swotS').innerHTML = listHtml(data.strengths);
            document.getElementById('swotW').innerHTML = listHtml(data.weaknesses);
            document.getElementById('swotO').innerHTML = listHtml(data.opportunities);
            document.getElementById('swotT').innerHTML = listHtml(data.threats);
            document.getElementById('swotResult').style.display = 'grid';
        })
        .catch(err => {
            btn.disabled = false;
            document.getElementById('swotLoading').style.display = 'none';
            document.getElementById('swotError').textContent = err.message;
            document.getElementById('swotError').style.display = 'block';
        });
}

function listHtml(items) {
    if (!items || items.length === 0) return '<p class="muted">Inga punkter.</p>';
    return '<ul>' + items.map(i => '<li>' + esc(i) + '</li>').join('') + '</ul>';
}

/* ── Copy generator (API call) ── */

function runCopy() {
    const context = document.getElementById('copyContext').value.trim();
    if (!context) { alert('Beskriv produkten eller sammanhanget.'); return; }

    const btn = document.getElementById('copyBtn');
    btn.disabled = true;
    document.getElementById('copyLoading').style.display = 'flex';
    document.getElementById('copyResult').style.display = 'none';
    document.getElementById('copyError').style.display = 'none';
    document.getElementById('copyPlaceholder').style.display = 'none';

    fetch('/api/tools/copy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            type: document.getElementById('copyType').value,
            context: context,
            audience: document.getElementById('copyAudience').value.trim(),
            tone: document.getElementById('copyTone').value,
        })
    })
        .then(r => r.json())
        .then(data => {
            btn.disabled = false;
            document.getElementById('copyLoading').style.display = 'none';
            if (data.error) {
                document.getElementById('copyError').textContent = data.error;
                document.getElementById('copyError').style.display = 'block';
                return;
            }
            document.getElementById('copyOutput').innerHTML = renderMarkdown(data.text);
            document.getElementById('copyResult').style.display = 'block';
        })
        .catch(err => {
            btn.disabled = false;
            document.getElementById('copyLoading').style.display = 'none';
            document.getElementById('copyError').textContent = err.message;
            document.getElementById('copyError').style.display = 'block';
        });
}

function copyCopyText() {
    const text = document.getElementById('copyOutput').innerText;
    navigator.clipboard.writeText(text).then(() => {
        const btn = document.getElementById('copyClipBtn');
        btn.textContent = 'Kopierat!';
        setTimeout(() => { btn.innerHTML = '&#128203; Kopiera'; }, 1500);
    });
}

/* ── Markdown (reuse from chat) ── */

function renderMarkdown(text) {
    let html = esc(text);
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (m, lang, code) =>
        '<pre class="md-code-block"><code>' + code.trim() + '</code></pre>');
    html = html.replace(/`([^`]+)`/g, '<code class="md-inline-code">$1</code>');
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    html = html.replace(/((?:^|\n)- .+(?:\n- .+)*)/g, block => {
        const items = block.trim().split('\n');
        return '<ul>' + items.map(i => '<li>' + i.replace(/^- /, '') + '</li>').join('') + '</ul>';
    });
    html = html.replace(/((?:^|\n)\d+\. .+(?:\n\d+\. .+)*)/g, block => {
        const items = block.trim().split('\n');
        return '<ol>' + items.map(i => '<li>' + i.replace(/^\d+\. /, '') + '</li>').join('') + '</ol>';
    });
    html = html.replace(/^### (.+)$/gm, '<h4>$1</h4>');
    html = html.replace(/^## (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^# (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/\n/g, '<br>');
    return html;
}

/* ── Util ── */

function fmt(n) {
    return new Intl.NumberFormat('sv-SE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n);
}

function esc(s) {
    if (!s) return '';
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}
