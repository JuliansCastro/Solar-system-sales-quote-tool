"""Shared chart payload builders for cotizacion views and reports."""

from .sizing import calcular_proyeccion_financiera, obtener_datos_pvgis


def build_cotizacion_charts_payload(cotizacion):
    """Build chart data payload used by frontend charts and PDF reports."""
    proyecto = cotizacion.proyecto
    cliente = proyecto.cliente

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
    generacion = float(proyecto.generacion_mensual_kwh or 0)
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
        'sizing': {
            'potencia_pico_kwp': proyecto.potencia_pico_kwp,
            'numero_paneles': proyecto.numero_paneles,
            'generacion_mensual_kwh': generacion,
            'porcentaje_cobertura': proyecto.porcentaje_cobertura,
            'capacidad_baterias_kwh': proyecto.capacidad_baterias_kwh,
            'autonomia_dias': proyecto.autonomia_dias,
        },
    }
