"""Shared chart payload builders for cotizacion views and reports."""

from decimal import Decimal
from core.models import Equipo
from core.calculations.sizing import calcular_proyeccion_financiera, obtener_datos_pvgis


def _calculate_sizing_from_items(cotizacion, proyecto):
    """
    Calculate sizing results based on selected equipment items in the quote.
    
    This is the SINGLE SOURCE OF TRUTH for all sizing data displayed in cotizacion_detail.html:
    - HTML section "Resultados del Dimensionamiento" uses this via context
    - All charts and comparisons use this via cotizacion_charts_data endpoint
    
    Returns a dict with:
    - potencia_pico_kwp: Total power from all panels
    - numero_paneles: Total number of panels
    - generacion_mensual_kwh: Estimated monthly generation (power × HSP × 30)
    - porcentaje_cobertura: Percentage of consumption covered by solar
    - capacidad_baterias_kwh: Total battery capacity if applicable
    - autonomia_dias: Days of autonomy from project config
    """
    items = cotizacion.items.select_related('equipo').all()
    
    # Calculate power from panels (in kW)
    panel_items = [item for item in items if item.equipo.categoria == Equipo.Categoria.PANEL]
    potencia_pico_kw = sum(
        float(item.equipo.potencia_nominal_w or 0) * int(item.cantidad or 0) 
        for item in panel_items
    ) / 1000
    numero_paneles = sum(int(item.cantidad or 0) for item in panel_items)
    
    # Calculate generation (kWh/month) using HSP from project
    hsp = float(proyecto.hsp_promedio or 5.0)  # Default to 5 hours if not set
    generacion_mensual_kwh = potencia_pico_kw * hsp * 30
    
    # Calculate battery capacity from battery items (in kWh)
    bateria_items = [item for item in items if item.equipo.categoria == Equipo.Categoria.BATERIA]
    capacidad_baterias_kwh = 0
    for item in bateria_items:
        # Try to get capacity from technical data (JSON field)
        datos_tec = item.equipo.datos_tecnicos or {}
        if 'capacidad_kwh' in datos_tec:
            capacidad_baterias_kwh += float(datos_tec['capacidad_kwh']) * int(item.cantidad or 0)
        elif 'capacidad_ah' in datos_tec and 'voltaje_nominal' in datos_tec:
            # Calculate from Ah and V: kWh = (Ah × V) / 1000
            capacidad_kwh = (float(datos_tec['capacidad_ah']) * float(datos_tec['voltaje_nominal'])) / 1000
            capacidad_baterias_kwh += capacidad_kwh * int(item.cantidad or 0)
        else:
            # Fallback: use potencia_nominal_w as reference (less accurate but something)
            capacidad_baterias_kwh += (float(item.equipo.potencia_nominal_w or 0) / 1000) * int(item.cantidad or 0)
    
    # Calculate coverage percentage (vs monthly consumption)
    consumo_mensual_kwh = float(proyecto.consumo_mensual_efectivo_kwh or 0)
    porcentaje_cobertura = 0
    if consumo_mensual_kwh > 0:
        porcentaje_cobertura = min(100, (generacion_mensual_kwh / consumo_mensual_kwh) * 100)
    
    # Calculate area required (approx 2.58 m² per panel of ~550W)
    area_panel_m2 = 2.278 * 1.134  # ~2.58 m²
    area_requerida_m2 = numero_paneles * area_panel_m2 if numero_paneles > 0 else 0
    
    return {
        'potencia_pico_kwp': round(potencia_pico_kw, 2),
        'numero_paneles': numero_paneles,
        'generacion_mensual_kwh': round(generacion_mensual_kwh, 0),
        'porcentaje_cobertura': round(porcentaje_cobertura, 1),
        'capacidad_baterias_kwh': round(capacidad_baterias_kwh, 2),
        'autonomia_dias': proyecto.autonomia_dias,
        'area_requerida_m2': round(area_requerida_m2, 1),
    }


def build_cotizacion_charts_payload(cotizacion):
    """
    Build chart data payload used by frontend charts and PDF reports.
    
    COHERENCE GUARANTEE: All sizing calculations use _calculate_sizing_from_items()
    ensuring that data shown in cotizacion_detail.html HTML and JavaScript charts
    are always synchronized and consistent.
    
    Returns JSON with:
    - costo_por_componente: Cost distribution by equipment category
    - consumo_comparacion: Current vs solar-supplied consumption
    - ahorro_dinero: Financial savings breakdown
    - proyeccion_financiera: ROI projection data
    - radiacion_mensual: Monthly solar radiation (PVGIS)
    - hsp_mensual: Monthly peak solar hours
    - sizing: Calculated sizing results (source of truth)
    """
    proyecto = cotizacion.proyecto
    cliente = proyecto.cliente

    # Calculate sizing from items (overrides proyecto values)
    sizing_from_items = _calculate_sizing_from_items(cotizacion, proyecto)
    generacion = float(sizing_from_items['generacion_mensual_kwh'])

    # Cost distribution by category
    items = cotizacion.items.select_related('equipo').all()
    cost_by_category = {}
    for item in items:
        categoria = item.equipo.get_categoria_display()
        cost_by_category[categoria] = cost_by_category.get(categoria, 0) + float(item.subtotal)

    if float(cotizacion.costo_instalacion) > 0:
        cost_by_category['Instalacion'] = float(cotizacion.costo_instalacion)
    if float(cotizacion.costo_transporte) > 0:
        cost_by_category['Transporte'] = float(cotizacion.costo_transporte)

    # Consumption comparison
    consumo = float(cliente.consumo_mensual_kwh or 0)

    # Financial projection
    ahorro_anual = float(proyecto.ahorro_mensual or 0) * 12
    costo = float(proyecto.costo_total or 0)
    proyeccion = calcular_proyeccion_financiera(
        ahorro_anual_cop=ahorro_anual,
        costo_sistema=costo,
    )

    # Monthly savings comparison
    gasto_actual = consumo * float(cliente.tarifa_electrica or 0)
    gasto_con_solar = max(0, (consumo - generacion)) * float(cliente.tarifa_electrica or 0)

    # PVGIS data for radiation and HSP charts
    radiacion_mensual = []
    hsp_mensual = []
    hsp_promedio = 0
    if proyecto.latitud is not None and proyecto.longitud is not None:
        pvgis_data = obtener_datos_pvgis(proyecto.latitud, proyecto.longitud)
        if pvgis_data.radiacion_mensual:
            radiacion_mensual = [r['radiacion_kwh_m2'] for r in pvgis_data.radiacion_mensual]
            hsp_mensual = [r['hsp'] for r in pvgis_data.radiacion_mensual]
        hsp_promedio = pvgis_data.hsp_promedio or 0

    return {
        'costo_por_componente': {
            'labels': list(cost_by_category.keys()),
            'values': list(cost_by_category.values()),
        },
        'consumo_comparacion': {
            'labels': ['Consumo actual', 'Con sistema solar'],
            'actual': consumo,
            'con_solar': max(0, consumo - generacion),
            'generacion': generacion,
        },
        'ahorro_dinero': {
            'gasto_actual': gasto_actual,
            'gasto_con_solar': gasto_con_solar,
            'ahorro_mensual': gasto_actual - gasto_con_solar,
        },
        'proyeccion_financiera': proyeccion,
        'roi_anos': proyecto.roi_anos,
        'radiacion_mensual': radiacion_mensual,
        'hsp_mensual': hsp_mensual,
        'hsp_promedio': hsp_promedio,
        'sizing': sizing_from_items,
    }
