let allProducts = [];
let currentStoreId = null;

function initProducts(storeId) {
    currentStoreId = storeId;
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
            '<p class="muted">Inga produkter ännu. Klicka "+ Lägg till produkt" för att börja.</p></div>';
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
        html += '<button class="btn btn-sm btn-danger" style="margin-left:auto;" onclick="deleteProduct(' + p.id + ')">Ta bort</button>';
        html += '</div></div></div>';
    });

    grid.innerHTML = html;
}

function openAddProduct() {
    document.getElementById('npTitle').value = '';
    document.getElementById('npPrice').value = '0';
    document.getElementById('npCost').value = '0';
    document.getElementById('npInventory').value = '0';
    document.getElementById('npSku').value = '';
    document.getElementById('npVendor').value = '';
    document.getElementById('addProductModal').classList.add('active');
}

function closeAddProduct() {
    document.getElementById('addProductModal').classList.remove('active');
}

function saveProduct() {
    const title = document.getElementById('npTitle').value.trim();
    if (!title) { alert('Produktnamn krävs.'); return; }

    const body = {
        store_id: currentStoreId,
        title: title,
        price: parseFloat(document.getElementById('npPrice').value) || 0,
        cost: parseFloat(document.getElementById('npCost').value) || 0,
        inventory: parseInt(document.getElementById('npInventory').value) || 0,
        sku: document.getElementById('npSku').value.trim(),
        vendor: document.getElementById('npVendor').value.trim(),
    };

    fetch('/api/local/products', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body),
    })
    .then(r => r.json())
    .then(data => {
        if (data.error) { alert(data.error); return; }
        closeAddProduct();
        initProducts(currentStoreId);
    })
    .catch(err => alert('Fel: ' + err.message));
}

function deleteProduct(id) {
    if (!confirm('Ta bort denna produkt?')) return;
    fetch('/api/local/products/' + id, { method: 'DELETE' })
        .then(() => initProducts(currentStoreId))
        .catch(err => alert('Fel: ' + err.message));
}

function fmt(n) {
    return new Intl.NumberFormat('sv-SE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n);
}

function esc(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}

document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal-overlay')) {
        e.target.classList.remove('active');
    }
});
