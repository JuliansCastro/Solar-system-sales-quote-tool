"""
Solar System Sizing Engine.

Contains all engineering calculations for:
- On-Grid systems: peak power, energy generation, savings, ROI.
- Off-Grid systems: battery bank, inverter, charge controller, panel array.
- PVGIS API integration for solar radiation data.

Reference:
- HSP = Horas Solar Pico (Peak Sun Hours)
- kWp = kilowatt-peak (panel rated power)
- DOD = Depth of Discharge (battery)
"""

import math
import requests
from dataclasses import dataclass, field
from typing import Optional
from django.conf import settings


# ──────────────────────────────────────────────
# DATA CLASSES FOR RESULTS
# ──────────────────────────────────────────────

@dataclass
class OnGridResult:
    """Results for on-grid system sizing."""
    potencia_pico_kwp: float = 0.0
    numero_paneles: int = 0
    potencia_panel_w: float = 0.0
    generacion_mensual_kwh: float = 0.0
    generacion_anual_kwh: float = 0.0
    porcentaje_cobertura: float = 0.0
    ahorro_mensual_cop: float = 0.0
    ahorro_anual_cop: float = 0.0
    costo_estimado_sistema: float = 0.0
    roi_anos: float = 0.0
    ahorro_acumulado_25_anos: float = 0.0
    co2_evitado_ton_ano: float = 0.0
    area_requerida_m2: float = 0.0
    inversor_potencia_kw: float = 0.0


@dataclass
class OffGridResult:
    """Results for off-grid system sizing."""
    # Loads
    potencia_total_w: float = 0.0
    energia_diaria_wh: float = 0.0
    potencia_pico_arranque_w: float = 0.0

    # Panels
    potencia_pico_kwp: float = 0.0
    numero_paneles: int = 0
    potencia_panel_w: float = 0.0
    area_paneles_m2: float = 0.0

    # Batteries
    capacidad_banco_kwh: float = 0.0
    capacidad_banco_ah: float = 0.0
    voltaje_sistema: int = 48
    numero_baterias: int = 0
    baterias_serie: int = 0
    baterias_paralelo: int = 0
    autonomia_dias: int = 1

    # Inverter
    inversor_potencia_w: float = 0.0
    inversor_potencia_arranque_w: float = 0.0

    # Charge controller
    regulador_corriente_a: float = 0.0

    # Financial
    generacion_mensual_kwh: float = 0.0
    costo_estimado_sistema: float = 0.0
    ahorro_mensual_cop: float = 0.0
    ahorro_anual_cop: float = 0.0
    roi_anos: float = 0.0
    ahorro_acumulado_25_anos: float = 0.0
    co2_evitado_ton_ano: float = 0.0
    area_requerida_m2: float = 0.0


@dataclass
class PVGISData:
    """Solar radiation data from PVGIS API."""
    radiacion_mensual: list = field(default_factory=list)  # kWh/m² per month
    radiacion_anual: float = 0.0  # kWh/m² per year
    hsp_promedio: float = 0.0  # Average HSP
    hsp_minimo: float = 0.0  # Worst month HSP
    mes_minimo: int = 0  # Month with lowest radiation
    temperatura_promedio: float = 0.0
    error: str = ''


# ──────────────────────────────────────────────
# PVGIS API INTEGRATION
# ──────────────────────────────────────────────

def obtener_datos_pvgis(lat: float, lon: float, year: int = 2023) -> PVGISData:
    """
    Fetch monthly solar radiation data from PVGIS API v5.3.

    Args:
        lat: Latitude (-90 to 90).
        lon: Longitude (-180 to 180).
        year: Year for data (default 2023).

    Returns:
        PVGISData with monthly and annual radiation values.
    """
    result = PVGISData()

    try:
        url = f"{settings.PVGIS_API_BASE_URL}/MRcalc"
        params = {
            'lat': lat,
            'lon': lon,
            'startyear': year,
            'endyear': year,
            'horirrad': 1,
            'outputformat': 'json',
        }

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if 'outputs' in data and 'monthly' in data['outputs']:
            monthly = data['outputs']['monthly']
            radiacion_mensual = []
            for m in monthly:
                # H(h)_m = Monthly irradiation on horizontal plane (kWh/m²)
                rad = m.get('H(h)_m', 0)
                radiacion_mensual.append({
                    'mes': m.get('month', 0),
                    'radiacion_kwh_m2': rad,
                    'hsp': rad / 30,  # Convert monthly to daily average
                })

            result.radiacion_mensual = radiacion_mensual
            result.radiacion_anual = sum(r['radiacion_kwh_m2'] for r in radiacion_mensual)

            hsp_values = [r['hsp'] for r in radiacion_mensual]
            result.hsp_promedio = sum(hsp_values) / len(hsp_values) if hsp_values else 0
            result.hsp_minimo = min(hsp_values) if hsp_values else 0
            result.mes_minimo = hsp_values.index(min(hsp_values)) + 1 if hsp_values else 0

    except requests.exceptions.RequestException as e:
        result.error = f"Error conectando con PVGIS: {str(e)}"
    except (KeyError, ValueError) as e:
        result.error = f"Error procesando datos PVGIS: {str(e)}"

    return result


# ──────────────────────────────────────────────
# ON-GRID SIZING
# ──────────────────────────────────────────────

def dimensionar_on_grid(
    consumo_mensual_kwh: float,
    tarifa_cop_kwh: float,
    hsp: float = 4.5,
    potencia_panel_w: float = 550,
    eficiencia_sistema: float = 0.80,
    porcentaje_cobertura_deseado: float = 100,
    costo_watt_instalado: float = 3500,
    incremento_tarifa_anual: float = 5.0,
    vida_util_anos: int = 25,
    degradacion_anual: float = 0.5,
) -> OnGridResult:
    """
    Size an on-grid (grid-tied) solar system.

    Args:
        consumo_mensual_kwh: Monthly electricity consumption (kWh).
        tarifa_cop_kwh: Electricity tariff (COP/kWh).
        hsp: Peak Sun Hours (daily average).
        potencia_panel_w: Panel wattage (W).
        eficiencia_sistema: Overall system efficiency (0-1).
        porcentaje_cobertura_deseado: Desired coverage (%).
        costo_watt_instalado: Cost per installed watt (COP/W).
        incremento_tarifa_anual: Annual tariff increase (%).
        vida_util_anos: System lifetime (years).
        degradacion_anual: Annual panel degradation (%).

    Returns:
        OnGridResult with all calculated values.
    """
    result = OnGridResult()
    result.potencia_panel_w = potencia_panel_w

    # Target monthly generation
    generacion_objetivo = consumo_mensual_kwh * (porcentaje_cobertura_deseado / 100)

    # Required peak power (kWp)
    # Formula: kWp = Egenerated / (HSP × 30 × efficiency)
    if hsp > 0 and eficiencia_sistema > 0:
        potencia_kwp = generacion_objetivo / (hsp * 30 * eficiencia_sistema)
    else:
        potencia_kwp = 0

    result.potencia_pico_kwp = round(potencia_kwp, 2)

    # Number of panels
    potencia_panel_kw = potencia_panel_w / 1000
    if potencia_panel_kw > 0:
        result.numero_paneles = math.ceil(potencia_kwp / potencia_panel_kw)

    # Actual peak power (adjusted to whole panels)
    potencia_real_kwp = result.numero_paneles * potencia_panel_kw
    result.potencia_pico_kwp = round(potencia_real_kwp, 2)

    # Monthly generation
    result.generacion_mensual_kwh = round(
        potencia_real_kwp * hsp * 30 * eficiencia_sistema, 1
    )
    result.generacion_anual_kwh = round(result.generacion_mensual_kwh * 12, 1)

    # Coverage
    if consumo_mensual_kwh > 0:
        result.porcentaje_cobertura = round(
            (result.generacion_mensual_kwh / consumo_mensual_kwh) * 100, 1
        )

    # Financial
    result.ahorro_mensual_cop = round(
        min(result.generacion_mensual_kwh, consumo_mensual_kwh) * tarifa_cop_kwh, 0
    )
    result.ahorro_anual_cop = round(result.ahorro_mensual_cop * 12, 0)

    # System cost
    result.costo_estimado_sistema = round(
        potencia_real_kwp * 1000 * costo_watt_instalado, 0
    )

    # ROI calculation (with tariff increase and degradation)
    if result.ahorro_anual_cop > 0:
        inversion = result.costo_estimado_sistema
        acumulado = 0
        for ano in range(1, vida_util_anos + 1):
            factor_tarifa = (1 + incremento_tarifa_anual / 100) ** (ano - 1)
            factor_degradacion = (1 - degradacion_anual / 100) ** (ano - 1)
            ahorro_ano = result.ahorro_anual_cop * factor_tarifa * factor_degradacion
            acumulado += ahorro_ano
            if acumulado >= inversion and result.roi_anos == 0:
                # Interpolate for fraction of year
                ahorro_previo = acumulado - ahorro_ano
                fraccion = (inversion - ahorro_previo) / ahorro_ano if ahorro_ano > 0 else 0
                result.roi_anos = round(ano - 1 + fraccion, 1)

        result.ahorro_acumulado_25_anos = round(acumulado, 0)

        if result.roi_anos == 0:
            result.roi_anos = vida_util_anos  # Never pays back in lifetime

    # CO2 avoided (Colombian grid emission factor ≈ 0.126 tCO2/MWh)
    result.co2_evitado_ton_ano = round(
        result.generacion_anual_kwh * 0.000126, 2
    )

    # Area required (approx 2m² per panel of ~550W)
    area_panel_m2 = (2.278 * 1.134) if potencia_panel_w >= 500 else (1.755 * 1.038)
    result.area_requerida_m2 = round(result.numero_paneles * area_panel_m2, 1)

    # Inverter sizing (typically 80-100% of array kWp)
    result.inversor_potencia_kw = round(potencia_real_kwp * 0.9, 1)

    return result


# ──────────────────────────────────────────────
# OFF-GRID SIZING
# ──────────────────────────────────────────────

def dimensionar_off_grid(
    cargas: list,
    hsp: float = 4.5,
    autonomia_dias: int = 1,
    potencia_panel_w: float = 550,
    voltaje_bateria: float = 12.0,
    capacidad_bateria_ah: float = 200,
    dod: float = 0.50,
    eficiencia_inversor: float = 0.93,
    eficiencia_bateria: float = 0.90,
    eficiencia_cableado: float = 0.97,
    voltaje_sistema: int = 48,
    factor_seguridad: float = 1.25,
) -> OffGridResult:
    """
    Size an off-grid solar system based on electrical loads.

    Args:
        cargas: List of dicts with keys: potencia_w, cantidad, horas_dia,
                factor_potencia, factor_arranque, carga_reactiva.
        hsp: Peak Sun Hours (daily average).
        autonomia_dias: Days of battery autonomy.
        potencia_panel_w: Panel wattage (W).
        voltaje_bateria: Single battery voltage (V).
        capacidad_bateria_ah: Single battery capacity (Ah).
        dod: Depth of Discharge (0-1).
        eficiencia_inversor: Inverter efficiency (0-1).
        eficiencia_bateria: Battery charge/discharge efficiency (0-1).
        eficiencia_cableado: Wiring efficiency (0-1).
        voltaje_sistema: System bus voltage (12, 24, 48V).
        factor_seguridad: Safety factor (typically 1.2-1.3).

    Returns:
        OffGridResult with all calculated values.
    """
    result = OffGridResult()
    result.potencia_panel_w = potencia_panel_w
    result.voltaje_sistema = voltaje_sistema
    result.autonomia_dias = autonomia_dias

    # 1. LOAD ANALYSIS
    potencia_total = 0
    energia_diaria = 0
    potencia_arranque_max = 0

    for carga in cargas:
        pot = carga.get('potencia_w', 0) * carga.get('cantidad', 1)
        horas = carga.get('horas_dia', 0)
        fp = carga.get('factor_potencia', 1.0)
        fa = carga.get('factor_arranque', 1.0)

        # Apparent power (VA)
        potencia_aparente = pot / fp if fp > 0 else pot

        potencia_total += potencia_aparente
        energia_diaria += pot * horas  # Wh/day (active power)

        # Startup surge
        pot_arranque = pot * fa
        if pot_arranque > potencia_arranque_max:
            potencia_arranque_max = pot_arranque

    result.potencia_total_w = round(potencia_total, 1)
    result.energia_diaria_wh = round(energia_diaria, 1)
    result.potencia_pico_arranque_w = round(potencia_arranque_max, 1)

    # 2. TOTAL SYSTEM EFFICIENCY
    eficiencia_total = eficiencia_inversor * eficiencia_bateria * eficiencia_cableado

    # 3. PANEL ARRAY SIZING
    # Energy needed from panels = daily load / efficiencies
    energia_paneles_wh = energia_diaria / eficiencia_total * factor_seguridad

    if hsp > 0:
        potencia_pico_w = energia_paneles_wh / hsp
        result.potencia_pico_kwp = round(potencia_pico_w / 1000, 2)
        result.numero_paneles = math.ceil(potencia_pico_w / potencia_panel_w)
    else:
        result.numero_paneles = 0

    # Actual peak power
    potencia_real_w = result.numero_paneles * potencia_panel_w
    result.potencia_pico_kwp = round(potencia_real_w / 1000, 2)

    # Panel area
    area_panel = (2.278 * 1.134) if potencia_panel_w >= 500 else (1.755 * 1.038)
    result.area_paneles_m2 = round(result.numero_paneles * area_panel, 1)

    # 4. BATTERY BANK SIZING
    # Required capacity = (daily energy × autonomy) / (DOD × battery efficiency)
    if dod > 0 and eficiencia_bateria > 0:
        capacidad_requerida_wh = (
            energia_diaria * autonomia_dias * factor_seguridad
        ) / (dod * eficiencia_bateria)
    else:
        capacidad_requerida_wh = 0

    result.capacidad_banco_kwh = round(capacidad_requerida_wh / 1000, 2)
    result.capacidad_banco_ah = round(capacidad_requerida_wh / voltaje_sistema, 1)

    # Battery configuration
    if voltaje_bateria > 0 and capacidad_bateria_ah > 0:
        result.baterias_serie = int(voltaje_sistema / voltaje_bateria)
        capacidad_ah_por_string = capacidad_bateria_ah
        result.baterias_paralelo = math.ceil(
            result.capacidad_banco_ah / capacidad_ah_por_string
        )
        result.numero_baterias = result.baterias_serie * result.baterias_paralelo

    # 5. INVERTER SIZING
    # Must handle continuous load + startup surge
    result.inversor_potencia_w = round(potencia_total * factor_seguridad, 0)
    result.inversor_potencia_arranque_w = round(
        max(potencia_arranque_max, potencia_total) * factor_seguridad, 0
    )

    # 6. CHARGE CONTROLLER SIZING
    # Corriente = Potencia paneles / Voltaje sistema × 1.25
    if voltaje_sistema > 0:
        result.regulador_corriente_a = round(
            (potencia_real_w / voltaje_sistema) * 1.25, 1
        )

    # Monthly generation estimate
    result.generacion_mensual_kwh = round(
        result.potencia_pico_kwp * hsp * 30 * eficiencia_total, 1
    )

    # 7. FINANCIAL ESTIMATES
    # Cost per watt installed (off-grid is higher due to batteries)
    costo_watt_instalado = 5000  # COP/W (higher than on-grid)
    result.costo_estimado_sistema = round(
        potencia_real_w * costo_watt_instalado, 0
    )

    # Area required
    result.area_requerida_m2 = result.area_paneles_m2

    # CO2 avoided (Colombian grid emission factor ≈ 0.126 tCO2/MWh)
    generacion_anual_kwh = result.generacion_mensual_kwh * 12
    result.co2_evitado_ton_ano = round(
        generacion_anual_kwh * 0.000126, 2
    )

    return result


# ──────────────────────────────────────────────
# EQUIPMENT SUGGESTION
# ──────────────────────────────────────────────

def sugerir_equipos(proyecto, resultado):
    """
    Suggest available equipment from inventory based on sizing results.

    Args:
        proyecto: Proyecto model instance.
        resultado: OnGridResult or OffGridResult.

    Returns:
        dict with suggested equipment per category.
    """
    from .models import Equipo

    tipo = proyecto.tipo_sistema
    sugerencias = {}

    # Filter by system compatibility
    base_qs = Equipo.objects.filter(activo=True, stock__gt=0)
    if tipo == 'on_grid':
        base_qs = base_qs.filter(sistema_compatible__in=['on_grid', 'ambos'])
    elif tipo == 'off_grid':
        base_qs = base_qs.filter(sistema_compatible__in=['off_grid', 'ambos'])

    # Panels - closest to required power
    paneles = base_qs.filter(categoria='panel').order_by('-potencia_nominal_w')
    if paneles.exists():
        # Find best matching panel
        best_panel = paneles.first()
        for panel in paneles:
            if panel.potencia_nominal_w >= resultado.potencia_panel_w:
                best_panel = panel
                break
        sugerencias['paneles'] = {
            'equipo': best_panel,
            'cantidad': resultado.numero_paneles,
        }

    # Inverter
    inversores = base_qs.filter(categoria='inversor').order_by('potencia_nominal_w')
    if inversores.exists():
        if isinstance(resultado, OnGridResult):
            potencia_inv = resultado.inversor_potencia_kw * 1000
        else:
            potencia_inv = resultado.inversor_potencia_w

        best_inv = inversores.last()
        for inv in inversores:
            if inv.potencia_nominal_w >= potencia_inv:
                best_inv = inv
                break
        sugerencias['inversores'] = {
            'equipo': best_inv,
            'cantidad': 1,
        }

    # Batteries (off-grid only)
    if isinstance(resultado, OffGridResult) and resultado.numero_baterias > 0:
        baterias = base_qs.filter(categoria='bateria').order_by('-potencia_nominal_w')
        if baterias.exists():
            sugerencias['baterias'] = {
                'equipo': baterias.first(),
                'cantidad': resultado.numero_baterias,
            }

        # Charge controller
        reguladores = base_qs.filter(categoria='regulador').order_by('corriente_nominal')
        if reguladores.exists():
            best_reg = reguladores.last()
            for reg in reguladores:
                if reg.corriente_nominal and reg.corriente_nominal >= resultado.regulador_corriente_a:
                    best_reg = reg
                    break
            sugerencias['reguladores'] = {
                'equipo': best_reg,
                'cantidad': 1,
            }

    # Structure
    estructuras = base_qs.filter(categoria='estructura')
    if estructuras.exists():
        sugerencias['estructuras'] = {
            'equipo': estructuras.first(),
            'cantidad': resultado.numero_paneles,  # 1 per panel typically
        }

    return sugerencias


# ──────────────────────────────────────────────
# FINANCIAL PROJECTIONS
# ──────────────────────────────────────────────

def calcular_proyeccion_financiera(
    ahorro_anual_cop: float,
    costo_sistema: float,
    vida_util: int = 25,
    incremento_tarifa: float = 5.0,
    degradacion: float = 0.5,
) -> dict:
    """
    Calculate year-by-year financial projection.

    Returns dict with lists for:
    - anos, ahorro_anual, ahorro_acumulado, flujo_neto
    """
    anos = []
    ahorro_anual_list = []
    ahorro_acumulado_list = []
    flujo_neto_list = []

    acumulado = -costo_sistema

    for ano in range(1, vida_util + 1):
        factor_tarifa = (1 + incremento_tarifa / 100) ** (ano - 1)
        factor_degradacion = (1 - degradacion / 100) ** (ano - 1)
        ahorro = ahorro_anual_cop * factor_tarifa * factor_degradacion

        acumulado += ahorro

        anos.append(ano)
        ahorro_anual_list.append(round(ahorro, 0))
        ahorro_acumulado_list.append(round(acumulado, 0))
        flujo_neto_list.append(round(ahorro, 0))

    return {
        'anos': anos,
        'ahorro_anual': ahorro_anual_list,
        'ahorro_acumulado': ahorro_acumulado_list,
        'flujo_neto': flujo_neto_list,
        'inversion_inicial': costo_sistema,
    }
