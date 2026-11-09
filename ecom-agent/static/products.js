let allProducts = [];

function initProducts(storeId) {
    fetch('/api/products/' + storeId)
        .then(r => r.json())
        .then(data => {
            if (data.error) { showProductsError(data.error); return; }
            allProducts = data;
            applyProductFilters();
            document.getElementById('productsLoading').style.display = 'none';
            document.getElementById('productsContent').style.display = 'block';
        })
        .catch(err => showProductsError(err.message));
}

function showProductsError(msg) {
    document.getElementById('productsLoading').style.display = 'none';
    document.getElementById('productsError').style.display = 'block';
    document.getElementById('productsErrorMsg').textContent = 'Kunde inte hämta produkter: ' + msg;
}

function applyProductFilters() {
    const search = document.getElementById('productSearch').value.toLowerCase().trim();
    const sort = document.getElementById('productSort').value;

    let filtered = allProducts.filter(p => {
        if (search && !p.title.toLowerCase().includes(search)) return false;
        return true;
    });

    filtered.sort((a, b) => {
        switch (sort) {
            case 'name_asc': return a.title.localeCompare(b.title, 'sv');
            case 'name_desc': return b.title.localeCompare(a.title, 'sv');
            case 'price_asc': return a.price - b.price;
            case 'price_desc': return b.price - a.price;
            case 'stock_asc': return a.inventory - b.inventory;
            case 'stock_desc': return b.inventory - a.inventory;
            default: return 0;
        }
    });

    renderProducts(filtered);
}

function renderProducts(products) {
    const grid = document.getElementById('productGrid');

    if (products.length === 0) {
        grid.innerHTML = '<div class="card" style="text-align:center;padding:48px;grid-column:1/-1;">' +
            '<p class="muted">Inga produkter matchar sökningen.</p></div>';
        return;
    }

    let html = '';
    products.forEach(p => {
        const stockCls = p.inventory < 5 ? 'stock-badge-red' :
            p.inventory <= 20 ? 'stock-badge-yellow' : 'stock-badge-green';
        const statusBadge = p.status === 'draft'
            ? '<span class="badge badge-warning">Utkast</span>'
            : '<span class="badge badge-success">Aktiv</span>';

        html += '<div class="product-card">';
        if (p.image) {
            html += '<div class="product-img" style="background-image:url(\'' + esc(p.image) + '\')"></div>';
        } else {
            html += '<div class="product-img product-img-placeholder"><span>Ingen bild</span></div>';
        }
        html += '<div class="product-info">';
        html += '<h3 class="product-title">' + esc(p.title) + '</h3>';
        if (p.vendor) {
            html += '<p class="product-vendor">' + esc(p.vendor) + '</p>';
        }
        html += '<div class="product-meta">';
        html += '<span class="product-price">' + fmt(p.price) + ' kr</span>';
        html += '<span class="stock-badge ' + stockCls + '">' + p.inventory + ' i lager</span>';
        html += '</div>';
        html += '<div class="product-footer">' + statusBadge;
        if (p.variants_count > 1) {
            html += '<span class="muted">' + p.variants_count + ' varianter</span>';
        }
        html += '</div></div></div>';
    });

    grid.innerHTML = html;
}

function fmt(n) {
    return new Intl.NumberFormat('sv-SE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n);
}

function esc(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}
