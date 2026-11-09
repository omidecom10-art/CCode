let allOrders = [];
let filteredOrders = [];
let currentPage = 1;
const perPage = 50;
let expandedRow = null;

function initOrders(storeId) {
    fetch('/api/orders/' + storeId)
        .then(r => r.json())
        .then(data => {
            if (data.error) { showOrdersError(data.error); return; }
            allOrders = data;
            applyFilters();
            document.getElementById('ordersLoading').style.display = 'none';
            document.getElementById('ordersContent').style.display = 'block';
        })
        .catch(err => showOrdersError(err.message));
}

function showOrdersError(msg) {
    document.getElementById('ordersLoading').style.display = 'none';
    document.getElementById('ordersError').style.display = 'block';
    document.getElementById('ordersErrorMsg').textContent = 'Kunde inte hämta ordrar: ' + msg;
}

function applyFilters() {
    const status = document.getElementById('filterStatus').value;
    const from = document.getElementById('filterFrom').value;
    const to = document.getElementById('filterTo').value;
    const search = document.getElementById('filterSearch').value.toLowerCase().trim();

    filteredOrders = allOrders.filter(o => {
        if (status !== 'all') {
            if (status === 'refunded' && o.financial !== 'refunded') return false;
            if (status === 'fulfilled' && (o.fulfillment !== 'fulfilled' || o.financial === 'refunded')) return false;
            if (status === 'unfulfilled' && (o.fulfillment === 'fulfilled' || o.financial === 'refunded')) return false;
        }
        if (from) {
            const d = o.created_at.slice(0, 10);
            if (d < from) return false;
        }
        if (to) {
            const d = o.created_at.slice(0, 10);
            if (d > to) return false;
        }
        if (search) {
            const hay = (o.customer + ' ' + o.order_number + ' ' + o.email).toLowerCase();
            if (!hay.includes(search)) return false;
        }
        return true;
    });

    currentPage = 1;
    expandedRow = null;
    renderOrders();
}

function renderOrders() {
    const tbody = document.getElementById('ordersTableBody');
    tbody.innerHTML = '';

    const totalPages = Math.max(1, Math.ceil(filteredOrders.length / perPage));
    if (currentPage > totalPages) currentPage = totalPages;
    const start = (currentPage - 1) * perPage;
    const page = filteredOrders.slice(start, start + perPage);

    if (page.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:32px;" class="muted">Inga ordrar matchar filtret.</td></tr>';
        document.getElementById('pagination').innerHTML = '';
        return;
    }

    page.forEach(o => {
        const statusCls = o.financial === 'refunded' ? 'badge-danger' :
            o.fulfillment === 'fulfilled' ? 'badge-success' : 'badge-warning';
        const statusText = o.financial === 'refunded' ? 'Återbetald' :
            o.fulfillment === 'fulfilled' ? 'Uppfylld' : 'Ej uppfylld';
        const date = o.created_at ? o.created_at.slice(0, 16).replace('T', ' ') : '';
        const isExpanded = expandedRow === o.id;

        let row = '<tr class="order-row' + (isExpanded ? ' expanded' : '') + '" onclick="toggleOrderDetail(' + o.id + ')">' +
            '<td class="expand-icon">' + (isExpanded ? '&#9660;' : '&#9654;') + '</td>' +
            '<td>#' + esc(String(o.order_number)) + '</td>' +
            '<td>' + esc(date) + '</td>' +
            '<td>' + esc(o.customer) + '</td>' +
            '<td class="items-col">' + esc(o.items_summary) + '</td>' +
            '<td>' + fmt(parseFloat(o.total)) + ' ' + esc(o.currency) + '</td>' +
            '<td><span class="badge ' + statusCls + '">' + statusText + '</span></td>' +
            '</tr>';

        if (isExpanded) {
            row += '<tr class="order-detail-row"><td colspan="7">' +
                renderOrderDetail(o) + '</td></tr>';
        }

        tbody.innerHTML += row;
    });

    renderPagination(totalPages);
}

function renderOrderDetail(o) {
    let html = '<div class="order-detail">';

    html += '<div class="detail-grid">';
    html += '<div class="detail-section">' +
        '<h4>Leveransadress</h4>' +
        '<p>' + esc(o.shipping_name || 'Ej angiven') + '</p>' +
        '<p class="muted">' + esc(o.shipping_address || 'Ej angiven') + '</p>' +
        '</div>';
    html += '<div class="detail-section">' +
        '<h4>Betalning</h4>' +
        '<p>' + esc(capitalize(o.gateway) || 'Ej angiven') + '</p>' +
        '<p class="muted">' + esc(o.email || '') + '</p>' +
        '</div>';
    html += '</div>';

    html += '<h4 style="margin-top:16px;">Produkter</h4>';
    html += '<div class="detail-items">';
    o.items.forEach(item => {
        html += '<div class="detail-item">';
        if (item.image) {
            html += '<img src="' + esc(item.image) + '" alt="" class="detail-item-img">';
        } else {
            html += '<div class="detail-item-img detail-item-placeholder">Ingen bild</div>';
        }
        html += '<div class="detail-item-info">' +
            '<span class="detail-item-title">' + esc(item.title) + '</span>' +
            '<span class="muted">' + item.quantity + ' st &times; ' + fmt(parseFloat(item.price)) + ' ' + esc(o.currency) + '</span>' +
            (item.sku ? '<span class="muted">SKU: ' + esc(item.sku) + '</span>' : '') +
            '</div>';
        html += '</div>';
    });
    html += '</div></div>';
    return html;
}

function toggleOrderDetail(orderId) {
    expandedRow = expandedRow === orderId ? null : orderId;
    renderOrders();
}

function renderPagination(totalPages) {
    const el = document.getElementById('pagination');
    if (totalPages <= 1) { el.innerHTML = ''; return; }

    let html = '<span class="page-info">Sida ' + currentPage + ' av ' + totalPages +
        ' (' + filteredOrders.length + ' ordrar)</span><div class="page-btns">';

    if (currentPage > 1) {
        html += '<button class="btn btn-sm btn-secondary" onclick="goPage(' + (currentPage - 1) + ')">&laquo; Föregående</button>';
    }

    const start = Math.max(1, currentPage - 2);
    const end = Math.min(totalPages, currentPage + 2);
    for (let i = start; i <= end; i++) {
        html += '<button class="btn btn-sm ' + (i === currentPage ? 'btn-primary' : 'btn-secondary') +
            '" onclick="goPage(' + i + ')">' + i + '</button>';
    }

    if (currentPage < totalPages) {
        html += '<button class="btn btn-sm btn-secondary" onclick="goPage(' + (currentPage + 1) + ')">Nästa &raquo;</button>';
    }
    html += '</div>';
    el.innerHTML = html;
}

function goPage(p) {
    currentPage = p;
    expandedRow = null;
    renderOrders();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function fmt(n) {
    return new Intl.NumberFormat('sv-SE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n);
}

function esc(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}

function capitalize(s) {
    if (!s) return '';
    return s.charAt(0).toUpperCase() + s.slice(1);
}
