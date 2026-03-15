/**
 * Real-Time Chart Update System
 * 
 * Updates charts dynamically based on selected equipment.
 * Provides chart explanations and persuasive text for each visualization.
 * 
 * Usage:
 *   const chartUpdater = new ChartUpdateSystem(proyectoId);
 *   window.addEventListener('equipmentRecalculated', (e) => {
 *     chartUpdater.updateAll(e.detail);
 *   });
 */

class ChartUpdateSystem {
  constructor(proyectoId) {
    this.proyectoId = proyectoId;
    this.currentData = {};
    
    // Chart configuration with explanations
    this.chartConfigs = {
      'consumo_generacion': {
        title: 'Consumo vs Generación Solar',
        explanation: 'Comparación entre el consumo actual de energía y lo que generará su sistema solar...',
      },
      'roi_acumulado': {
        title: 'Retorno de Inversión Acumulado',
        explanation: 'Proyección del ahorro acumulado a lo largo de 25 años del sistema solar...',
      },
      'radiacion_mensual': {
        title: 'Radiación Solar Mensual',
        explanation: 'Datos de radiación solar en el plano horizontal del sitio, proporcionados por PVGIS...',
      },
      'hsp_mensual': {
        title: 'Horas Solar Pico Mensuales',
        explanation: 'Promedio de horas equivalentes de pleno sol por día, según datos astronómicos...',
      },
    };
  }
  
  /**
   * Update all charts with new data
   */
  updateAll(resultado) {
    this.currentData = resultado;
    
    if (document.getElementById('chart-consumo')) {
      this.updateConsumoChart(resultado);
    }
    if (document.getElementById('chart-roi')) {
      this.updateROIChart(resultado);
    }
    if (document.getElementById('chart-radiacion')) {
      this.updateRadiacionChart();
    }
    if (document.getElementById('chart-hsp')) {
      this.updateHSPChart();
    }
  }
  
  /**
   * Update consumption vs generation chart
   */
  updateConsumoChart(resultado) {
    const consumoActual = parseFloat(document.querySelector('[data-consumo-actual]')?.dataset.consumoActual || '0');
    const generacionSolar = resultado.generacion_mensual_kwh;
    const consumoRestante = Math.max(0, consumoActual - generacionSolar);
    
    // Update Plotly chart if available
    if (typeof Plotly !== 'undefined' && document.getElementById('chart-consumo')) {
      Plotly.restyle('chart-consumo', {
        y: [[consumoActual, generacionSolar, consumoRestante]],
        text: [[
          consumoActual.toFixed(0) + ' kWh',
          generacionSolar.toFixed(0) + ' kWh',
          consumoRestante.toFixed(0) + ' kWh'
        ]],
      });
    }
    
    // Update explanation
    this.updateChartExplanation('chart-consumo', {
      title: 'Consumo vs Generación Solar',
      subtitle: `Cobertura solar: ${resultado.porcentaje_cobertura.toFixed(1)}%`,
      explanation: `
        <p>Su sistema solar generará <strong>${generacionSolar.toFixed(0)} kWh mensuales</strong>, 
        cubriendo el <strong>${resultado.porcentaje_cobertura.toFixed(1)}%</strong> de su consumo actual 
        de ${consumoActual.toFixed(0)} kWh.</p>
        
        ${resultado.porcentaje_cobertura >= 100 ? 
          '<p class="text-green-700 font-semibold">🎉 ¡Su sistema producirá más energía de la que consume!</p>' :
          `<p>Deberá seguir comprando <strong>${consumoRestante.toFixed(0)} kWh mensuales</strong> de la red 
          eléctrica, representando un ahorro del ${resultado.porcentaje_cobertura.toFixed(1)}%.</p>`
        }
      `,
      keyPoints: [
        `Generación solar: ${generacionSolar.toFixed(0)} kWh/mes`,
        `Consumo cubierto: ${consumoActual} kWh/mes`,
        `Cobertura: ${resultado.porcentaje_cobertura.toFixed(1)}%`,
        resultado.porcentaje_cobertura >= 100 ? 'Autosuficiencia energética: ✓' : `Compra de red: ${consumoRestante.toFixed(0)} kWh/mes`,
      ],
    });
  }
  
  /**
   * Update ROI chart
   */
  updateROIChart(resultado) {
    // Would update ROI chart with new calculations
    this.updateChartExplanation('chart-roi', {
      title: 'Retorno de Inversión',
      subtitle: `ROI: ${resultado.roi_anos.toFixed(1)} años`,
      explanation: `
        <p>Su inversión de <strong>$${resultado.costo_estimado_sistema.toLocaleString('es-CO')}</strong> 
        se recuperará en aproximadamente <strong>${resultado.roi_anos.toFixed(1)} años</strong>.</p>
        
        <p>Después de ese período, su sistema continuará generando ahorros limpios durante 
        los ${(25 - resultado.roi_anos).toFixed(0)} años restantes de vida útil.</p>
        
        <p class="text-green-700 font-semibold">
          Ahorro acumulado en 25 años: $${resultado.ahorro_acumulado_25_anos.toLocaleString('es-CO')}
        </p>
      `,
      keyPoints: [
        `Inversión inicial: $${resultado.costo_estimado_sistema.toLocaleString('es-CO')}`,
        `Ahorro mensual: $${resultado.ahorro_mensual_cop.toLocaleString('es-CO')}`,
        `Ahorro anual: $${resultado.ahorro_anual_cop.toLocaleString('es-CO')}`,
        `Recuperación: ${resultado.roi_anos.toFixed(1)} años`,
        `Ahorro 25 años: $${resultado.ahorro_acumulado_25_anos.toLocaleString('es-CO')}`,
      ],
    });
  }
  
  /**
   * Update radiation chart
   */
  updateRadiacionChart() {
    // Would update radiacion chart  
    this.updateChartExplanation('chart-radiacion', {
      title: 'Radiación Solar Mensual',
      subtitle: 'Datos de PVGIS',
      explanation: `
        <p>La radiación solar varía según la estación. Este gráfico muestra la <strong>radiación en el plano 
        horizontal</strong> para su ubicación, medida en kWh/m² por mes.</p>
        
        <p>Los meses con <span class="text-red-600">menor radiación</span> requieren sistemas de mayor capacidad 
        para garantizar la generación deseada durante todo el año.</p>
      `,
      keyPoints: [
        'Radiación mínima en meses de invierno',
        'Radiación máxima en meses de verano',
        'El sistema está dimensionado para el mes con menor radiación',
      ],
    });
  }
  
  /**
   * Update HSP chart
   */
  updateHSPChart() {
    // Would update HSP chart
    this.updateChartExplanation('chart-hsp', {
      title: 'Horas Solar Pico (HSP)',
      subtitle: 'Disponibilidad solar diaria',
      explanation: `
        <p>Las "Horas Solar Pico" (HSP) son el número equivalente de horas a plena radiación solar 
        (1000 W/m²) necesarias para que un panel genere su energía diaria.</p>
        
        <p>Por ejemplo: Si tiene HSP = 4.5 horas/día, un panel de 100W genera 450Wh diariamente.</p>
        
        <p>El sistema está dimensionado usando el HSP promedio de su zona: <strong>4.5 horas/día</strong></p>
      `,
      keyPoints: [
        'HSP promedio: 4.5 horas/día',
        'Varía entre 2 y 6 horas según la estación',
        'Usado para cálculos de generación esperada',
      ],
    });
  }
  
  /**
   * Update chart explanation text
   */
  updateChartExplanation(chartId, config) {
    const container = document.querySelector(`[data-chart-id="${chartId}"]`);
    if (!container) return;
    
    // Try to find explanation block
    const explanationBlock = container.querySelector('.chart-explanation');
    if (!explanationBlock) return;
    
    explanationBlock.innerHTML = `
      <div class="border-t border-canvas-200 mt-4 pt-4">
        <details class="space-y-2">
          <summary class="cursor-pointer font-semibold text-ink-800 hover:text-solar-600 transition-colors">
            <i class="fas fa-info-circle text-solar-500 mr-2"></i>
            Entender este gráfico
          </summary>
          
          <div class="mt-3 p-4 bg-canvas-50 rounded space-y-3">
            ${config.subtitle ? `<h4 class="font-semibold text-ink-900">${config.subtitle}</h4>` : ''}
            
            <div class="text-sm text-ink-700 space-y-2">
              ${config.explanation}
            </div>
            
            ${config.keyPoints ? `
              <div class="border-t border-canvas-200 pt-3">
                <p class="font-semibold text-ink-800 mb-2">Puntos clave:</p>
                <ul class="list-disc list-inside space-y-1 text-sm text-ink-700">
                  ${config.keyPoints.map(point => `<li>${point}</li>`).join('')}
                </ul>
              </div>
            ` : ''}
            
            ${config.recommendations ? `
              <div class="border-t border-canvas-200 pt-3 p-3 bg-blue-50 rounded">
                <p class="font-semibold text-blue-900 mb-2">💡 Recomendación:</p>
                <p class="text-sm text-blue-800">${config.recommendations}</p>
              </div>
            ` : ''}
          </div>
        </details>
      </div>
    `;
  }
  
  /**
   * Format currency
   */
  formatCurrency(value) {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      maximumFractionDigits: 0,
    }).format(value);
  }
  
  /**
   * Format number
   */
  formatNumber(value, decimals = 2) {
    return parseFloat(value).toLocaleString('es-CO', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  }
}

// Export for use
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ChartUpdateSystem;
}
