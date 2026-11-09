let revenueChart = null;
let ordersChart = null;
let currentStoreId = null;

function fmt(num) {
    return new Intl.NumberFormat('sv-SE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(num);
}

function loadDashboard(storeId) {
    currentStoreId = storeId;
    document.getElementById('dashboardLoading').style.display = 'block';
    document.getElementById('dashboardContent').style.display = 'none';
    document.getElementById('dashboardError').style.display = 'none';

    fetch('/api/dashboard/' + storeId)
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                showError(data.error);
                return;
            }
            renderDashboard(data);
        })
        .catch(err => showError(err.message));
}

function refreshDashboard() {
    if (!currentStoreId) return;
    const btn = document.getElementById('refreshBtn');
    btn.disabled = true;
    btn.textContent = 'Uppdaterar...';

    document.getElementById('dashboardLoading').style.display = 'block';
    document.getElementById('dashboardContent').style.display = 'none';
    document.getElementById('dashboardError').style.display = 'none';

    fetch('/api/refresh/' + currentStoreId, { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            btn.disabled = false;
            btn.innerHTML = '&#8635; Uppdatera';
            if (data.error) {
                showError(data.error);
                return;
            }
            renderDashboard(data);
        })
        .catch(err => {
            btn.disabled = false;
            btn.innerHTML = '&#8635; Uppdatera';
            showError(err.message);
        });
}

function showError(msg) {
    document.getElementById('dashboardLoading').style.display = 'none';
    document.getElementById('dashboardContent').style.display = 'none';
    document.getElementById('dashboardError').style.display = 'block';
    document.getElementById('errorMsg').textContent = 'Kunde inte hämta data: ' + msg;
}

function renderDashboard(data) {
    document.getElementById('dashboardLoading').style.display = 'none';
    document.getElementById('dashboardError').style.display = 'none';
    document.getElementById('dashboardContent').style.display = 'block';

    // KPI
    document.getElementById('kpiToday').textContent = fmt(data.kpi.revenue_today) + ' kr';
    document.getElementById('kpiWeek').textContent = fmt(data.kpi.revenue_week) + ' kr';
    document.getElementById('kpiMonth').textContent = fmt(data.kpi.revenue_month) + ' kr';
    document.getElementById('kpiOrders').textContent = data.kpi.total_orders;
    document.getElementById('kpiAvg').textContent = fmt(data.kpi.avg_order) + ' kr';

    // Status badges
    const badges = document.getElementById('statusBadges');
    badges.innerHTML = '';
    const statusLabels = {
        unfulfilled: { label: 'Ej uppfylld', cls: 'badge-warning' },
        fulfilled: { label: 'Uppfylld', cls: 'badge-success' },
        refunded: { label: 'Återbetald', cls: 'badge-danger' }
    };
    for (const [key, info] of Object.entries(statusLabels)) {
        const count = data.status[key] || 0;
        badges.innerHTML += '<span class="badge ' + info.cls + '">' + info.label + ': ' + count + '</span>';
    }

    // Top products
    const topEl = document.getElementById('topProducts');
    if (data.top_products.length === 0) {
        topEl.innerHTML = '<p class="muted">Ingen data ännu.</p>';
    } else {
        let html = '';
        data.top_products.forEach((p, i) => {
            html += '<div class="top-product-item">' +
                '<span class="top-rank">' + (i + 1) + '</span>' +
                '<span class="top-name">' + escHtml(p.name) + '</span>' +
                '<span class="top-rev">' + fmt(p.revenue) + ' kr</span>' +
                '</div>';
        });
        topEl.innerHTML = html;
    }

    // Low stock
    const stockEl = document.getElementById('lowStock');
    if (data.low_stock.length === 0) {
        stockEl.innerHTML = '<p class="muted">Alla produkter har tillräckligt lager.</p>';
    } else {
        let html = '';
        data.low_stock.forEach(item => {
            const cls = item.quantity <= 0 ? 'stock-zero' : 'stock-low';
            html += '<div class="stock-item ' + cls + '">' +
                '<div class="stock-info">' +
                '<span class="stock-name">' + escHtml(item.product) + '</span>' +
                '<span class="stock-variant">' + escHtml(item.variant) + '</span>' +
                '</div>' +
                '<span class="stock-qty">' + item.quantity + ' st</span>' +
                '</div>';
        });
        stockEl.innerHTML = html;
    }

    // Recent orders table
    const tbody = document.getElementById('ordersTable');
    tbody.innerHTML = '';
    data.recent_orders.forEach(order => {
        const statusCls = order.fulfillment === 'fulfilled' ? 'badge-success' :
            order.financial === 'refunded' ? 'badge-danger' : 'badge-warning';
        const statusText = order.fulfillment === 'fulfilled' ? 'Uppfylld' :
            order.financial === 'refunded' ? 'Återbetald' : 'Ej uppfylld';

        tbody.innerHTML += '<tr>' +
            '<td>#' + order.id + '</td>' +
            '<td>' + order.date + '</td>' +
            '<td>' + escHtml(order.customer) + '</td>' +
            '<td>' + escHtml(order.items) + '</td>' +
            '<td>' + fmt(parseFloat(order.total)) + ' ' + order.currency + '</td>' +
            '<td><span class="badge ' + statusCls + '">' + statusText + '</span></td>' +
            '</tr>';
    });

    // Charts
    renderCharts(data.chart);
}

function renderCharts(chart) {
    const style = getComputedStyle(document.documentElement);
    const accent = style.getPropertyValue('--accent').trim() || '#6C5CE7';
    const border = style.getPropertyValue('--border').trim() || '#2a2a2a';
    const textMuted = style.getPropertyValue('--text-muted').trim() || '#888888';

    const shortLabels = chart.labels.map(d => d.slice(5));

    const gridOpts = {
        color: border,
    };
    const tickOpts = {
        color: textMuted,
        font: { size: 11 },
    };

    if (revenueChart) revenueChart.destroy();
    if (ordersChart) ordersChart.destroy();

    revenueChart = new Chart(document.getElementById('revenueChart'), {
        type: 'line',
        data: {
            labels: shortLabels,
            datasets: [{
                label: 'Intäkter (kr)',
                data: chart.revenue,
                borderColor: accent,
                backgroundColor: accent + '22',
                fill: true,
                tension: 0.3,
                pointRadius: 2,
                pointHoverRadius: 5,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => fmt(ctx.parsed.y) + ' kr'
                    }
                }
            },
            scales: {
                x: { grid: gridOpts, ticks: tickOpts },
                y: { grid: gridOpts, ticks: { ...tickOpts, callback: v => fmt(v) } }
            }
        }
    });

    ordersChart = new Chart(document.getElementById('ordersChart'), {
        type: 'bar',
        data: {
            labels: shortLabels,
            datasets: [{
                label: 'Ordrar',
                data: chart.orders,
                backgroundColor: accent + '88',
                borderColor: accent,
                borderWidth: 1,
                borderRadius: 4,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: { grid: gridOpts, ticks: tickOpts },
                y: { grid: gridOpts, ticks: { ...tickOpts, stepSize: 1 } }
            }
        }
    });
}

function escHtml(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
}
