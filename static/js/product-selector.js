/**
 * Dynamic Product Selector for Recurring Order Creation
 * TC-024: AJAX-based product selection with search, filter, and quantity spinners
 * 
 * Usage:
 * <div id="product-selector"></div>
 * <script>
 *   new ProductSelector('#product-selector', {
 *     endpoint: '/marketplace/api/products/',
 *     onSelectionChange: (products) => console.log('Selected:', products)
 *   });
 * </script>
 */

class ProductSelector {
  constructor(selector, options = {}) {
    this.container = document.querySelector(selector);
    if (!this.container) {
      console.error('ProductSelector: Container not found:', selector);
      return;
    }

    this.endpoint = options.endpoint || '/marketplace/api/products/';
    this.onSelectionChange = options.onSelectionChange || (() => {});
    this.selectedProducts = new Map(); // product_id -> quantity

    this.init();
  }

  async init() {
    this.container.innerHTML = this.getTemplate();
    this.attachEventListeners();
    await this.loadProducts();
  }

  getTemplate() {
    return `
      <div class="product-selector">
        <div class="product-selector-controls mb-3">
          <div class="input-group">
            <input 
              type="text" 
              class="form-control product-search-input" 
              placeholder="Search products..."
              aria-label="Search products"
            />
            <button class="btn btn-outline-secondary product-filter-btn" type="button">
              Filter
            </button>
          </div>
          <div class="product-filter-options mt-2" style="display: none;">
            <label class="form-check">
              <input type="checkbox" class="form-check-input product-filter-in-season" checked />
              <span class="form-check-label">In season only</span>
            </label>
            <label class="form-check">
              <input type="checkbox" class="form-check-input product-filter-organic" />
              <span class="form-check-label">Organic certified</span>
            </label>
          </div>
        </div>

        <div class="product-list" style="max-height: 400px; overflow-y: auto; border: 1px solid #ddd; border-radius: 4px;">
          <div class="text-center py-4 text-muted">
            <small>Loading products...</small>
          </div>
        </div>

        <div class="product-selector-summary mt-3">
          <p><strong>Selected Products:</strong> <span class="selected-count">0</span></p>
          <div class="selected-products-list"></div>
        </div>
      </div>
    `;
  }

  attachEventListeners() {
    // Search input
    const searchInput = this.container.querySelector('.product-search-input');
    searchInput.addEventListener('keyup', () => this.handleSearch());

    // Filter button
    const filterBtn = this.container.querySelector('.product-filter-btn');
    const filterOptions = this.container.querySelector('.product-filter-options');
    filterBtn.addEventListener('click', () => {
      filterOptions.style.display = 
        filterOptions.style.display === 'none' ? 'block' : 'none';
    });

    // Filter checkboxes
    this.container.querySelector('.product-filter-in-season')
      .addEventListener('change', () => this.handleSearch());
    this.container.querySelector('.product-filter-organic')
      .addEventListener('change', () => this.handleSearch());
  }

  async loadProducts(params = {}) {
    try {
      const queryParams = new URLSearchParams({
        limit: 100,
        in_season: 'true',
        ...params,
      });

      const response = await fetch(`${this.endpoint}?${queryParams}`);
      const data = await response.json();

      this.renderProducts(data.products || []);
    } catch (error) {
      console.error('Error loading products:', error);
      this.container.querySelector('.product-list').innerHTML = 
        '<div class="alert alert-danger m-2">Error loading products</div>';
    }
  }

  renderProducts(products) {
    const list = this.container.querySelector('.product-list');

    if (products.length === 0) {
      list.innerHTML = '<div class="text-center py-4 text-muted">No products found</div>';
      return;
    }

    const html = products.map(product => `
      <div class="product-item p-3 border-bottom d-flex justify-content-between align-items-center">
        <div class="product-info flex-grow-1">
          <div class="font-weight-bold">${this.escapeHtml(product.name)}</div>
          <small class="text-muted">
            ${this.escapeHtml(product.producer)} • 
            ${this.escapeHtml(product.category)} • 
            ${product.price_display}
          </small>
          <div class="mt-1">
            <span class="badge badge-info">${product.stock_qty} in stock</span>
            <span class="badge ${product.available ? 'badge-success' : 'badge-secondary'}">
              ${product.available ? 'Available' : 'Unavailable'}
            </span>
          </div>
        </div>
        <div class="product-selector-controls ml-3">
          <div class="input-group input-group-sm">
            <input 
              type="number" 
              class="form-control product-qty-input" 
              value="0"
              min="0"
              max="${product.stock_qty}"
              data-product-id="${product.id}"
              data-product-name="${this.escapeHtml(product.name)}"
              aria-label="Quantity"
            />
            <span class="input-group-text">qty</span>
          </div>
        </div>
      </div>
    `).join('');

    list.innerHTML = html;

    // Attach quantity input listeners
    list.querySelectorAll('.product-qty-input').forEach(input => {
      input.addEventListener('change', () => this.handleQuantityChange(input));
    });
  }

  handleQuantityChange(input) {
    const productId = input.dataset.productId;
    const qty = parseInt(input.value) || 0;

    if (qty > 0) {
      this.selectedProducts.set(productId, qty);
    } else {
      this.selectedProducts.delete(productId);
    }

    this.updateSummary();
    this.onSelectionChange(Object.fromEntries(this.selectedProducts));
  }

  updateSummary() {
    const count = this.selectedProducts.size;
    this.container.querySelector('.selected-count').textContent = count;

    const summaryList = this.container.querySelector('.selected-products-list');
    if (count === 0) {
      summaryList.innerHTML = '<small class="text-muted">No products selected</small>';
      return;
    }

    const items = Array.from(this.selectedProducts.entries())
      .map(([id, qty]) => {
        const input = this.container.querySelector(`[data-product-id="${id}"]`);
        const name = input ? input.dataset.productName : `Product ${id}`;
        return `<div class="small"><strong>${name}</strong>: ${qty} qty</div>`;
      })
      .join('');

    summaryList.innerHTML = items;
  }

  async handleSearch() {
    const search = this.container.querySelector('.product-search-input').value;
    const inSeasonOnly = this.container.querySelector('.product-filter-in-season').checked;

    await this.loadProducts({
      search: search || undefined,
      in_season: inSeasonOnly ? 'true' : undefined,
    });
  }

  escapeHtml(text) {
    const map = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;',
    };
    return text.replace(/[&<>"']/g, m => map[m]);
  }

  /**
   * Get selected products as object { product_id: quantity, ... }
   */
  getSelectedProducts() {
    return Object.fromEntries(this.selectedProducts);
  }

  /**
   * Get selected products as array of { id, name, quantity }
   */
  getSelectedProductsArray() {
    return Array.from(this.selectedProducts.entries()).map(([id, qty]) => ({
      id,
      quantity: qty,
      name: this.container.querySelector(`[data-product-id="${id}"]`)?.dataset.productName || '',
    }));
  }

  /**
   * Clear all selections
   */
  clear() {
    this.selectedProducts.clear();
    this.container.querySelectorAll('.product-qty-input').forEach(input => {
      input.value = 0;
    });
    this.updateSummary();
    this.onSelectionChange({});
  }
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ProductSelector;
}
