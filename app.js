const grid = document.querySelector('#product-grid');
const search = document.querySelector('#search');
const categoryFilter = document.querySelector('#category-filter');
const formatFilter = document.querySelector('#format-filter');
const resultCount = document.querySelector('#result-count');
const pagination = document.querySelector('#pagination');
const dialog = document.querySelector('#product-dialog');
const pageState = { page: 1, pageSize: 8, totalPages: 0, total: 0 };
let requestController;
let searchTimer;
let detailRequest = 0;

function formatPrice(value, currency) {
  return new Intl.NumberFormat('es-CL', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(value);
}

async function getJson(url, signal) {
  const response = await fetch(url, { signal });
  const body = await response.json();
  if (!response.ok) {
    throw new Error(body.error || `Error del servidor (${response.status})`);
  }
  return body;
}

function showGridState(kind, title, message, actionLabel, action) {
  const state = document.createElement('div');
  state.className = `inline-state ${kind}`;
  const icon = document.createElement('span');
  icon.className = `state-icon${kind === 'loading' ? ' spinner' : ''}`;
  icon.setAttribute('aria-hidden', 'true');
  if (kind !== 'loading') icon.textContent = kind === 'error' ? '!' : '⌕';
  const heading = document.createElement('strong');
  heading.textContent = title;
  const description = document.createElement('p');
  description.textContent = message;
  state.append(icon, heading, description);
  if (actionLabel && action) {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = actionLabel;
    button.addEventListener('click', action);
    state.append(button);
  }
  grid.replaceChildren(state);
}

function productCard(product) {
  const article = document.createElement('article');
  article.className = 'product-card';
  const button = document.createElement('button');
  button.className = 'card-button';
  button.type = 'button';
  button.dataset.productId = product.id;
  button.setAttribute('aria-label', `Ver detalle de ${product.name}`);

  const imageWrap = document.createElement('span');
  imageWrap.className = 'image-wrap';
  const image = document.createElement('img');
  image.src = product.imageUrl;
  image.alt = '';
  image.loading = 'lazy';
  const index = document.createElement('span');
  index.className = 'card-index';
  index.textContent = `#${product.id}`;
  imageWrap.append(image, index);

  const copy = document.createElement('span');
  copy.className = 'card-copy';
  const category = document.createElement('span');
  category.className = 'card-type';
  category.textContent = product.category.split(' > ')[0];
  const name = document.createElement('strong');
  name.textContent = product.name;
  const meta = document.createElement('span');
  meta.className = 'card-meta';
  meta.textContent = `${product.format} · ${formatPrice(product.price, product.currency)}`;
  const detail = document.createElement('span');
  detail.className = 'view-link';
  detail.textContent = 'Ver detalle →';
  copy.append(category, name, meta, detail);
  button.append(imageWrap, copy);
  article.append(button);
  return article;
}

function renderPagination() {
  pagination.replaceChildren();
  if (pageState.totalPages < 2) return;

  const addButton = (label, page, disabled = false) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = label;
    button.disabled = disabled;
    button.addEventListener('click', () => {
      pageState.page = page;
      loadProducts();
    });
    pagination.append(button);
  };

  addButton('← Anterior', pageState.page - 1, pageState.page === 1);
  const pages = document.createElement('div');
  pages.className = 'pages';
  const first = Math.max(1, Math.min(pageState.page - 2, pageState.totalPages - 4));
  const last = Math.min(pageState.totalPages, first + 4);
  for (let page = first; page <= last; page += 1) {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = String(page);
    if (page === pageState.page) {
      button.className = 'active';
      button.setAttribute('aria-current', 'page');
    }
    button.addEventListener('click', () => {
      pageState.page = page;
      loadProducts();
    });
    pages.append(button);
  }
  addButton('Siguiente →', pageState.page + 1, pageState.page === pageState.totalPages);
  pagination.insertBefore(pages, pagination.lastElementChild);
}

function renderProducts(data) {
  pageState.page = data.page;
  pageState.totalPages = data.totalPages;
  pageState.total = data.total;
  grid.replaceChildren(...data.items.map(productCard));
  resultCount.textContent = data.total === 0
    ? 'No se encontraron productos'
    : `Mostrando ${(data.page - 1) * data.pageSize + 1}-${Math.min(data.page * data.pageSize, data.total)} de ${data.total.toLocaleString('es-CL')}`;
  if (data.items.length === 0) {
    showGridState('empty', 'Sin resultados', 'Prueba con otra búsqueda o elimina algunos filtros.', 'Limpiar filtros', clearFilters);
  }
  renderPagination();
}

async function loadProducts() {
  if (requestController) requestController.abort();
  requestController = new AbortController();
  const { signal } = requestController;
  const params = new URLSearchParams({
    page: String(pageState.page),
    pageSize: String(pageState.pageSize),
  });
  if (search.value.trim()) params.set('q', search.value.trim());
  if (categoryFilter.value) params.set('category', categoryFilter.value);
  if (formatFilter.value) params.set('format', formatFilter.value);

  showGridState('loading', 'Cargando productos', 'Espera mientras consultamos el catálogo.');
  resultCount.textContent = 'Cargando catálogo...';
  try {
    const data = await getJson(`/api/products?${params}`, signal);
    if (!signal.aborted) renderProducts(data);
  } catch (error) {
    if (error.name === 'AbortError') return;
    if (!signal.aborted) {
      showGridState('error', 'No pudimos cargar el catálogo', error.message, 'Reintentar', loadProducts);
      resultCount.textContent = 'Error al cargar el catálogo';
      pagination.replaceChildren();
    }
  }
}

function addOptions(select, values) {
  const placeholder = select.options[0];
  select.replaceChildren(placeholder);
  for (const value of values) {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = value;
    select.append(option);
  }
}

function clearFilters() {
  search.value = '';
  categoryFilter.value = '';
  formatFilter.value = '';
  pageState.page = 1;
  loadProducts();
}

async function initialize() {
  showGridState('loading', 'Cargando catálogo', 'Conectando con el servidor.');
  try {
    const filters = await getJson('/api/products/filters');
    addOptions(categoryFilter, filters.categories);
    addOptions(formatFilter, filters.formats);
    await loadProducts();
  } catch (error) {
    showGridState('error', 'No pudimos conectar con el catálogo', error.message, 'Reintentar', initialize);
    resultCount.textContent = 'Error al cargar el catálogo';
  }
}

function renderDetailState(title, message, retry) {
  document.querySelector('#detail-title').textContent = title;
  document.querySelector('#detail-description').textContent = message;
  document.querySelector('#detail-list').replaceChildren();
  document.querySelector('.product-commerce').hidden = true;
  const image = document.querySelector('#detail-image');
  image.removeAttribute('src');
  if (retry) {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = 'Reintentar';
    button.dataset.detailRetry = '';
    button.addEventListener('click', retry, { once: true });
    document.querySelector('.detail-copy').append(button);
  }
}

async function openDetail(productId) {
  const requestId = ++detailRequest;
  document.querySelector('[data-detail-retry]')?.remove();
  if (!dialog.open) dialog.showModal();
  document.querySelector('#detail-id').textContent = `PRODUCTO #${productId}`;
  renderDetailState('Cargando producto...', 'Consultando la información completa.');
  try {
    const product = await getJson(`/api/products/${encodeURIComponent(productId)}`);
    if (requestId !== detailRequest) return;
    document.querySelector('#detail-title').textContent = product.name;
    document.querySelector('#detail-description').textContent = product.description;
    const image = document.querySelector('#detail-image');
    image.src = product.imageUrl;
    image.alt = product.name;

    const details = [
      ['Categoría', product.category],
      ['Formato', product.format],
      ['Unidad de precio', product.priceUnit],
      ['Identificador', product.id],
    ];
    const list = document.querySelector('#detail-list');
    list.replaceChildren(...details.map(([label, value]) => {
      const wrapper = document.createElement('div');
      const term = document.createElement('dt');
      term.textContent = label;
      const description = document.createElement('dd');
      description.textContent = value;
      wrapper.append(term, description);
      return wrapper;
    }));
    document.querySelector('#detail-price').textContent = formatPrice(product.price, product.currency);
    document.querySelector('#detail-currency').textContent = `Moneda: ${product.currency}`;
    document.querySelector('#detail-original-price').textContent = `Precio original: ${formatPrice(product.originalPrice, product.currency)}`;
    document.querySelector('#detail-extracted-at').textContent = `Datos extraídos: ${product.extractedAt}`;
    const source = document.querySelector('#detail-source');
    source.href = product.productUrl;
    document.querySelector('.product-commerce').hidden = false;
    document.querySelector('[data-detail-retry]')?.remove();
  } catch (error) {
    if (error.name === 'AbortError') return;
    if (requestId !== detailRequest) return;
    renderDetailState('No pudimos cargar el producto', error.message, () => openDetail(productId));
  }
}

grid.addEventListener('click', (event) => {
  const button = event.target.closest('[data-product-id]');
  if (button) openDetail(button.dataset.productId);
});
document.querySelector('#dialog-close').addEventListener('click', () => dialog.close());
dialog.addEventListener('click', (event) => {
  if (event.target === dialog) dialog.close();
});

search.addEventListener('input', () => {
  window.clearTimeout(searchTimer);
  pageState.page = 1;
  searchTimer = window.setTimeout(loadProducts, 250);
});
[categoryFilter, formatFilter].forEach((control) => {
  control.addEventListener('change', () => {
    pageState.page = 1;
    loadProducts();
  });
});

initialize();
