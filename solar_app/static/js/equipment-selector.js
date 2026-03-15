/**
 * Equipment Selector Component
 * 
 * Modular, reusable component for selecting equipment during project sizing.
 * Provides:
 * - Real-time equipment filtering
 * - Equipment selection with quantity input
 * - Compatibility checking
 * - Live generation recalculation
 * 
 * Usage:
 *   const selector = new EquipmentSelector('#equipment-container', proyectoId);
 *   selector.init();
 */

class EquipmentSelector {
  constructor(container, proyectoId, options = {}) {
    this.container = document.querySelector(container);
    this.proyectoId = proyectoId;
    
    // Configuration
    this.apiBaseUrl = '/api';
    this.debounceDelay = 500;
    this.autoRecalculate = true;
    this.showNotifications = true;
    
    // Merge with options
    Object.assign(this, options);
    
    // State
    this.selectedEquipos = new Map();
    this.currentFilters = {};
    this.isCalculating = false;
    this.lastResult = null;
    
    // Bind methods
    this.handleFilterChange = this.handleFilterChange.bind(this);
    this.handleEquipoSelect = this.handleEquipoSelect.bind(this);
    this.handleEquipoRemove = this.handleEquipoRemove.bind(this);
  }
  
  /**
   * Initialize the component
   */
  async init() {
    this.render();
    this.attachEventListeners();
    await this.loadSelectedEquipment();
  }
  
  /**
   * Render the component structure
   */
  render() {
    this.container.innerHTML = `
      <div class="equipment-selector">
        <!-- Inventory Panel -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          <!-- Search & Filters -->
          <div class="lg:col-span-1 card p-6 h-fit">
            <h3 class="text-lg font-semibold text-ink-800 mb-4">
              <i class="fas fa-filter mr-2"></i>Filtrar inventario
            </h3>
            
            <div class="space-y-4">
              <!-- Equipment Type Filter -->
              <div>
                <label class="block text-sm font-medium text-ink-700 mb-2">
                  Tipo de equipo
                </label>
                <select id="filter-tipo" class="form-select w-full">
                  <option value="">Todos</option>
                  <option value="panel">Panel Solar</option>
                  <option value="inversor">Inversor</option>
                  <option value="estructura">Estructura</option>
                  <option value="regulador">Regulador</option>
                  <option value="bateria">Batería</option>
                </select>
              </div>
              
              <!-- Category Filter -->
              <div>
                <label class="block text-sm font-medium text-ink-700 mb-2">
                  Categoría
                </label>
                <select id="filter-categoria" class="form-select w-full">
                  <option value="">Todas</option>
                  <option value="panel">Panel Solar</option>
                  <option value="inversor">Inversor</option>
                  <option value="estructura">Estructura de montaje</option>
                  <option value="regulador">Regulador de carga</option>
                  <option value="bateria">Batería</option>
                  <option value="cable">Cableado</option>
                  <option value="accesorio">Accesorio</option>
                </select>
              </div>
              
              <!-- Manufacturer Filter -->
              <div>
                <label class="block text-sm font-medium text-ink-700 mb-2">
                  Fabricante
                </label>
                <input 
                  type="text" 
                  id="filter-fabricante" 
                  class="form-input w-full" 
                  placeholder="Ej: JinkoSolar"
                >
              </div>
              
              <!-- Power Range -->
              <div class="grid grid-cols-2 gap-2">
                <div>
                  <label class="block text-sm font-medium text-ink-700 mb-2">
                    Potencia mín (W)
                  </label>
                  <input 
                    type="number" 
                    id="filter-potencia-min" 
                    class="form-input w-full"
                    placeholder="0"
                    min="0"
                  >
                </div>
                <div>
                  <label class="block text-sm font-medium text-ink-700 mb-2">
                    Potencia máx (W)
                  </label>
                  <input 
                    type="number" 
                    id="filter-potencia-max" 
                    class="form-input w-full"
                    placeholder="5000"
                    min="0"
                  >
                </div>
              </div>
              
              <!-- Stock Filter -->
              <div>
                <label class="flex items-center">
                  <input 
                    type="checkbox" 
                    id="filter-stock" 
                    class="form-checkbox"
                  >
                  <span class="ml-2 text-sm text-ink-700">Solo disponibles</span>
                </label>
              </div>
              
              <!-- Search -->
              <div>
                <label class="block text-sm font-medium text-ink-700 mb-2">
                  Buscar
                </label>
                <input 
                  type="text" 
                  id="filter-search" 
                  class="form-input w-full" 
                  placeholder="Nombre, modelo, SKU..."
                >
              </div>
            </div>
          </div>
          
          <!-- Equipment List -->
          <div class="lg:col-span-2">
            <h3 class="text-lg font-semibold text-ink-800 mb-4">
              <i class="fas fa-th mr-2"></i>Equipos disponibles
            </h3>
            <div id="equipment-list" class="space-y-3" role="region" aria-live="polite">
              <div class="text-center py-8 text-ink-400">
                <i class="fas fa-spinner fa-spin text-2xl mb-2"></i>
                <p>Cargando equipos...</p>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Selected Equipment Summary -->
        <div class="card p-6">
          <h3 class="text-lg font-semibold text-ink-800 mb-4">
            <i class="fas fa-check-circle text-solar-500 mr-2"></i>Equipos seleccionados
          </h3>
          <div id="selected-equipment" class="space-y-2">
            <p class="text-ink-400 text-sm">Ningún equipo seleccionado aún</p>
          </div>
        </div>
      </div>
    `;
  }
  
  /**
   * Attach event listeners
   */
  attachEventListeners() {
    // Filter listeners
    ['filter-tipo', 'filter-categoria', 'filter-fabricante', 'filter-potencia-min', 
     'filter-potencia-max', 'filter-stock', 'filter-search'].forEach(filterId => {
      const element = document.getElementById(filterId);
      if (element) {
        element.addEventListener('change', this.debounce(() => {
          this.handleFilterChange();
        }, this.debounceDelay));
        
        // For text inputs, also handle 'input' event
        if (element.tagName === 'INPUT') {
          element.addEventListener('input', this.debounce(() => {
            this.handleFilterChange();
          }, this.debounceDelay));
        }
      }
    });
  }
  
  /**
   * Handle filter changes
   */
  async handleFilterChange() {
    this.currentFilters = {
      tipo_equipo: document.getElementById('filter-tipo').value,
      categoria_equipo: document.getElementById('filter-categoria').value,
      fabricante: document.getElementById('filter-fabricante').value,
      potencia_min: document.getElementById('filter-potencia-min').value,
      potencia_max: document.getElementById('filter-potencia-max').value,
      en_stock: document.getElementById('filter-stock').checked,
      buscar: document.getElementById('filter-search').value,
    };
    
    await this.loadEquipment();
  }
  
  /**
   * Load equipment list with current filters
   */
  async loadEquipment() {
    const listContainer = document.getElementById('equipment-list');
    listContainer.innerHTML = '<div class="text-center py-8 text-ink-400"><i class="fas fa-spinner fa-spin text-2xl mb-2"></i><p>Cargando...</p></div>';
    
    try {
      const params = new URLSearchParams(this.currentFilters);
      const response = await fetch(`${this.apiBaseUrl}/equipment/list/?${params}`);
      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Error al cargar equipos');
      }
      
      this.renderEquipmentList(data.equipos);
    } catch (error) {
      this.showError(`Error cargando equipos: ${error.message}`);
      listContainer.innerHTML = `<div class="text-center py-8 text-red-500"><i class="fas fa-exclamation-triangle mr-2"></i>${error.message}</div>`;
    }
  }
  
  /**
   * Render equipment list
   */
  renderEquipmentList(equipos) {
    const listContainer = document.getElementById('equipment-list');
    
    if (!equipos || equipos.length === 0) {
      listContainer.innerHTML = '<div class="text-center py-8 text-ink-400"><p>No hay equipos disponibles con esos filtros</p></div>';
      return;
    }
    
    listContainer.innerHTML = equipos.map(eq => `
      <div class="border border-canvas-200 rounded-lg p-4 hover:border-solar-300 transition-colors">
        <div class="flex items-start justify-between gap-4">
          <div class="flex-1">
            <h4 class="font-semibold text-ink-900">${eq.nombre}</h4>
            <p class="text-sm text-ink-500 mt-1">
              <i class="fas fa-bolt text-yellow-500 mr-1"></i>
              ${eq.potencia_w}W
              ${eq.eficiencia ? `• ${eq.eficiencia}% eficiencia` : ''}
            </p>
            <p class="text-sm text-ink-500">
              ${eq.en_stock ? `<span class="text-green-600"><i class="fas fa-check-circle mr-1"></i>${eq.stock} en stock</span>` : '<span class="text-red-600"><i class="fas fa-times-circle mr-1"></i>Sin stock</span>'}
            </p>
            <p class="text-lg font-bold text-solar-600 mt-2">
              $${eq.precio.toLocaleString('es-CO', {maximumFractionDigits: 0})}
            </p>
          </div>
          <div class="flex flex-col gap-2">
            <input 
              type="number" 
              class="equipment-quantity form-input w-20 text-center" 
              value="1" 
              min="1"
              max="${eq.stock}"
              data-equipo-id="${eq.id}"
              placeholder="Cant"
            >
            <button 
              class="btn btn-primary btn-sm equipment-select-btn" 
              data-equipo-id="${eq.id}"
              data-tipo="panel"
              ${!eq.en_stock ? 'disabled' : ''}
            >
              <i class="fas fa-plus mr-1"></i>Agregar
            </button>
          </div>
        </div>
      </div>
    `).join('');
    
    // Attach select handlers
    listContainer.querySelectorAll('.equipment-select-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const equipoId = e.target.closest('button').dataset.equipoId;
        const equipmentCard = e.target.closest('[data-equipo-id]');
        const cantidad = equipmentCard.querySelector('.equipment-quantity').value;
        this.selectEquipment(equipoId, cantidad);
      });
    });
  }
  
  /**
   * Select equipment
   */
  async selectEquipment(equipoId, cantidad = 1) {
    try {
      // Determine equipment type from the list
      const tipoEquipo = 'panel'; // Default, should be improved
      
      const response = await fetch(`${this.apiBaseUrl}/proyectos/${this.proyectoId}/equipment/select/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCookie('csrftoken'),
        },
        body: JSON.stringify({
          equipo_id: equipoId,
          tipo_equipo: tipoEquipo,
          cantidad: parseInt(cantidad),
        }),
      });
      
      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Error seleccionando equipo');
      }
      
      this.showSuccess(data.message);
      await this.loadSelectedEquipment();
      
      if (this.autoRecalculate) {
        await this.recalculate();
      }
    } catch (error) {
      this.showError(`Error: ${error.message}`);
    }
  }
  
  /**
   * Load selected equipment
   */
  async loadSelectedEquipment() {
    // This would typically load from a separate endpoint
    // For now, we'll maintain state on the client
  }
  
  /**
   * Recalculate generation
   */
  async recalculate() {
    if (this.isCalculating) return;
    
    this.isCalculating = true;
    
    try {
      const response = await fetch(`${this.apiBaseUrl}/proyectos/${this.proyectoId}/recalculate/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCookie('csrftoken'),
        },
      });
      
      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Error en recálculo');
      }
      
      this.lastResult = data.resultado;
      this.updateSelectedEquipmentDisplay(data.equipos_seleccionados);
      
      // Dispatch event for chart updates
      window.dispatchEvent(new CustomEvent('equipmentRecalculated', {
        detail: data.resultado,
      }));
      
      // Show warnings/alerts
      if (data.alertas && data.alertas.length > 0) {
        data.alertas.forEach(alert => {
          if (alert.tipo === 'critico') {
            this.showError(alert.mensaje);
          } else {
            this.showWarning(alert.mensaje);
          }
        });
      }
    } catch (error) {
      this.showError(`Error en recálculo: ${error.message}`);
    } finally {
      this.isCalculating = false;
    }
  }
  
  /**
   * Update selected equipment display
   */
  updateSelectedEquipmentDisplay(equipos) {
    const container = document.getElementById('selected-equipment');
    
    if (!equipos || equipos.length === 0) {
      container.innerHTML = '<p class="text-ink-400 text-sm">Ningún equipo seleccionado aún</p>';
      return;
    }
    
    container.innerHTML = `
      <div class="space-y-2">
        ${equipos.map(eq => `
          <div class="flex items-center justify-between p-3 bg-canvas-50 rounded border border-canvas-200">
            <div>
              <p class="font-medium text-ink-900">${eq.nombre}</p>
              <p class="text-sm text-ink-500">${eq.cantidad} x $${eq.precio_unitario.toLocaleString('es-CO', {maximumFractionDigits: 0})}</p>
            </div>
            <div class="text-right">
              <p class="font-semibold text-solar-600">$${eq.subtotal.toLocaleString('es-CO', {maximumFractionDigits: 0})}</p>
              <button class="text-xs text-red-600 hover:text-red-800 mt-1 remove-equipment" data-seleccion-id="${eq.id}">
                <i class="fas fa-trash mr-1"></i>Remover
              </button>
            </div>
          </div>
        `).join('')}
      </div>
    `;
    
    // Attach remove handlers
    container.querySelectorAll('.remove-equipment').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const seleccionId = e.target.closest('button').dataset.seleccionId;
        this.removeEquipment(seleccionId);
      });
    });
  }
  
  /**
   * Remove equipment
   */
  async removeEquipment(seleccionId) {
    if (!confirm('¿Remover este equipo?')) return;
    
    try {
      const response = await fetch(`${this.apiBaseUrl}/proyectos/${this.proyectoId}/equipment/${seleccionId}/remove/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': this.getCookie('csrftoken'),
        },
      });
      
      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Error removiendo equipo');
      }
      
      this.showSuccess(data.message);
      await this.loadSelectedEquipment();
      
      if (this.autoRecalculate) {
        await this.recalculate();
      }
    } catch (error) {
      this.showError(`Error: ${error.message}`);
    }
  }
  
  /**
   * Utility: Debounce function
   */
  debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }
  
  /**
   * Utility: Get CSRF token
   */
  getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let cookie of cookies) {
        cookie = cookie.trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }
  
  /**
   * Show success notification
   */
  showSuccess(message) {
    if (!this.showNotifications) return;
    // Implement based on your notification system
    console.log('success:', message);
  }
  
  /**
   * Show error notification
   */
  showError(message) {
    if (!this.showNotifications) return;
    console.error('error:', message);
  }
  
  /**
   * Show warning notification
   */
  showWarning(message) {
    if (!this.showNotifications) return;
    console.warn('warning:', message);
  }
}

// Export for use
if (typeof module !== 'undefined' && module.exports) {
  module.exports = EquipmentSelector;
}
