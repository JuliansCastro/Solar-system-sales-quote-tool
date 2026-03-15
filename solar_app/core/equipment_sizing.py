"""
Equipment-based Sizing Engine.

Modular calculation engine for solar system sizing based on actual selected equipment.
Calculates generation, losses, and financial metrics using real equipment specs from inventory.

Key functions:
- calculate_generation_with_equipment: Core calculation engine
- validate_equipment_compatibility: Compatibility checking
- estimate_system_losses: Loss estimation based on equipment
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
import math


# ──────────────────────────────────────────────
# DATA CLASSES
# ──────────────────────────────────────────────

@dataclass
class EquipmentSizingResult:
    """Results from equipment-based sizing calculation."""
    potencia_pico_kwp: float = 0.0
    numero_paneles: int = 0
    potencia_panel_w: float = 0.0
    potencia_real_kwp: float = 0.0
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
    
    # Equipment-specific fields
    perdidas_totales_porcentaje: float = 0.0
    perdidas_paneles_porcentaje: float = 0.0
    perdidas_inversor_porcentaje: float = 0.0
    perdidas_cableado_porcentaje: float = 0.0
    perdidas_transformador_porcentaje: float = 0.0
    
    # Warnings/validation messages
    alertas: List[Dict[str, str]] = None
    
    def __post_init__(self):
        if self.alertas is None:
            self.alertas = []


@dataclass
class CompatibilityIssue:
    """Representation of a compatibility issue between equipment."""
    es_critico: bool
    equipo1_nombre: str
    equipo2_nombre: str
    tipo_validacion: str
    mensaje: str
    parametro_afectado: str = ""


# ──────────────────────────────────────────────
# LOSS CALCULATION ENGINE
# ──────────────────────────────────────────────

def estimate_system_losses(
    selected_equipos: List[Dict],
    tipo_sistema: str = 'on_grid',
) -> Dict[str, float]:
    """
    Estimate system losses based on selected equipment.
    
    Args:
        selected_equipos: List of dicts with keys:
            - tipo: 'panel', 'inversor', 'cable', etc.
            - equipo: Equipo instance
            - cantidad: int
            - eficiencia: float (0-1)
        tipo_sistema: 'on_grid', 'off_grid', 'hybrid'
    
    Returns:
        Dict with loss percentages for each component and total.
    """
    losses = {
        'paneles': 2.0,  # Panel degradation and temperature
        'inversor': 3.0,  # Inversor efficiency loss
        'cableado': 1.5,  # Wiring losses
        'transformador': 0.5,  # Transformer loss (if present)
        'otros': 1.0,  # Other factors
        'total': 0.0,
    }
    
    # Adjust based on equipment selection
    for item in selected_equipos:
        tipo = item.get('tipo', '').lower()
        equipo = item.get('equipo')
        
        if not equipo:
            continue
        
        if tipo == 'panel':
            # Panel efficiency impact
            panel_loss = (1 - (equipo.eficiencia or 0.90) / 100) * 100
            losses['paneles'] = max(1.0, min(5.0, panel_loss))
            
        elif tipo == 'inversor':
            # Inversor efficiency impact
            inversor_loss = (1 - (equipo.eficiencia or 0.93) / 100) * 100
            losses['inversor'] = max(2.0, min(8.0, inversor_loss))
    
    # Calculate total loss using compound formula
    # Total loss ≈ 100 - (100 × (1 - loss1%)(1 - loss2%)...)
    loss_factors = [
        (100 - losses['paneles']) / 100,
        (100 - losses['inversor']) / 100,
        (100 - losses['cableado']) / 100,
        (100 - losses['transformador']) / 100,
        (100 - losses['otros']) / 100,
    ]
    
    combined_survival = 1.0
    for factor in loss_factors:
        combined_survival *= factor
    
    losses['total'] = round((1 - combined_survival) * 100, 2)
    
    return losses


# ──────────────────────────────────────────────
# COMPATIBILITY VALIDATION ENGINE
# ──────────────────────────────────────────────

def validate_equipment_compatibility(
    selected_equipos: List[Dict],
    compatibility_rules: List = None,
) -> Tuple[bool, List[CompatibilityIssue]]:
    """
    Validate compatibility between selected equipment.
    
    Args:
        selected_equipos: List of selected equipment dicts
        compatibility_rules: List of EquipoCompatibilidad instances
    
    Returns:
        Tuple (is_valid: bool, issues: List[CompatibilityIssue])
    """
    issues = []
    
    if not compatibility_rules:
        return True, issues
    
    # Extract equipment by type
    equipos_por_tipo = {}
    for item in selected_equipos:
        tipo = item.get('tipo', '').lower()
        equipo = item.get('equipo')
        if equipo:
            if tipo not in equipos_por_tipo:
                equipos_por_tipo[tipo] = []
            equipos_por_tipo[tipo].append(equipo)
    
    # Check each compatibility rule
    for rule in compatibility_rules:
        if not rule.activo:
            continue
        
        # Check if both equipment types are present
        base_presente = any(
            eq.id == rule.equipo_base_id
            for equipos in equipos_por_tipo.values()
            for eq in equipos
        )
        compat_presente = any(
            eq.id == rule.equipo_compatible_id
            for equipos in equipos_por_tipo.values()
            for eq in equipos
        )
        
        if base_presente and compat_presente:
            # Validate according to rule type
            if rule.tipo_validacion == 'voltaje':
                # Check voltage compatibility
                base = rule.equipo_base
                compat = rule.equipo_compatible
                
                if (base.voltaje_nominal and compat.voltaje_nominal and
                    abs(base.voltaje_nominal - compat.voltaje_nominal) > 5):
                    issues.append(CompatibilityIssue(
                        es_critico=rule.es_critico,
                        equipo1_nombre=f"{base.fabricante} {base.modelo}",
                        equipo2_nombre=f"{compat.fabricante} {compat.modelo}",
                        tipo_validacion=rule.get_tipo_validacion_display(),
                        mensaje=rule.mensaje_alerta or "Voltajes incompatibles",
                        parametro_afectado="voltaje",
                    ))
            
            elif rule.tipo_validacion == 'corriente':
                # Check current compatibility
                base = rule.equipo_base
                compat = rule.equipo_compatible
                
                if (base.corriente_nominal and compat.corriente_nominal):
                    if rule.valor_maximo and compat.corriente_nominal > rule.valor_maximo:
                        issues.append(CompatibilityIssue(
                            es_critico=rule.es_critico,
                            equipo1_nombre=f"{base.fabricante} {base.modelo}",
                            equipo2_nombre=f"{compat.fabricante} {compat.modelo}",
                            tipo_validacion=rule.get_tipo_validacion_display(),
                            mensaje=rule.mensaje_alerta or "Corriente fuera de rango",
                            parametro_afectado="corriente",
                        ))
    
    has_critical = any(issue.es_critico for issue in issues)
    return not has_critical, issues


# ──────────────────────────────────────────────
# MAIN SIZING CALCULATION ENGINE
# ──────────────────────────────────────────────

def calculate_generation_with_equipment(
    selected_equipos: List[Dict],
    consumo_mensual_kwh: float,
    hsp: float = 4.5,
    tarifa_cop_kwh: float = 750,
    porcentaje_cobertura_deseado: float = 100,
    costo_watt_instalado_base: float = 3500,
    incremento_tarifa_anual: float = 5.0,
    vida_util_anos: int = 25,
    degradacion_anual: float = 0.5,
    tipo_sistema: str = 'on_grid',
) -> EquipmentSizingResult:
    """
    Calculate system generation and financial metrics using actual selected equipment.
    
    This is the main calculation engine that performs real-time sizing based on
    user-selected equipment from inventory.
    
    Args:
        selected_equipos: List of dicts with selected equipment:
            {
                'tipo': 'panel' | 'inversor' | 'estructura' | 'regulador' | 'bateria',
                'equipo': Equipo instance,
                'cantidad': int,
                'notas': str (optional)
            }
        consumo_mensual_kwh: Target monthly consumption (kWh)
        hsp: Peak Sun Hours per day
        tarifa_cop_kwh: Electricity tariff (COP/kWh)
        porcentaje_cobertura_deseado: Desired coverage percentage (0-100)
        costo_watt_instalado_base: Base cost per watt installed (COP/W)
        incremento_tarifa_anual: Annual tariff increase (%)
        vida_util_anos: System lifetime (years)
        degradacion_anual: Annual panel degradation (%)
        tipo_sistema: System type ('on_grid', 'off_grid', 'hybrid')
    
    Returns:
        EquipmentSizingResult with all calculations.
    """
    result = EquipmentSizingResult()
    
    # Extract panels and other equipment
    paneles = [item for item in selected_equipos if item.get('tipo') == 'panel']
    inversores = [item for item in selected_equipos if item.get('tipo') == 'inversor']
    
    if not paneles:
        result.alertas.append({
            'tipo': 'error',
            'mensaje': 'Debe seleccionar al menos un panel solar',
        })
        return result
    
    if not inversores and tipo_sistema in ['on_grid', 'hybrid']:
        result.alertas.append({
            'tipo': 'error',
            'mensaje': 'Debe seleccionar al menos un inversor',
        })
        return result
    
    # 1. CALCULATE SYSTEM LOSSES
    losses = estimate_system_losses(selected_equipos, tipo_sistema)
    result.perdidas_paneles_porcentaje = losses['paneles']
    result.perdidas_inversor_porcentaje = losses['inversor']
    result.perdidas_cableado_porcentaje = losses['cableado']
    result.perdidas_transformador_porcentaje = losses['transformador']
    result.perdidas_totales_porcentaje = losses['total']
    
    # System efficiency (1 - total losses)
    eficiencia_sistema = 1.0 - (losses['total'] / 100)
    
    # 2. CALCULATE PANEL ARRAY
    potencia_total_panel_w = 0
    numero_paneles_total = 0
    costo_paneles = 0
    
    for item in paneles:
        equipo = item.get('equipo')
        cantidad = item.get('cantidad', 1)
        potencia_total_panel_w += equipo.potencia_nominal_w * cantidad
        numero_paneles_total += cantidad
        costo_paneles += float(equipo.precio_venta) * cantidad
    
    potencia_pico_kwp = potencia_total_panel_w / 1000
    result.potencia_pico_kwp = round(potencia_pico_kwp, 2)
    result.numero_paneles = numero_paneles_total
    result.potencia_panel_w = potencia_total_panel_w / numero_paneles_total if numero_paneles_total > 0 else 0
    result.potencia_real_kwp = result.potencia_pico_kwp
    
    # 3. CALCULATE GENERATION
    result.generacion_mensual_kwh = round(
        potencia_pico_kwp * hsp * 30 * eficiencia_sistema, 1
    )
    result.generacion_anual_kwh = round(result.generacion_mensual_kwh * 12, 1)
    
    # 4. COVERAGE PERCENTAGE
    if consumo_mensual_kwh > 0:
        result.porcentaje_cobertura = round(
            (result.generacion_mensual_kwh / consumo_mensual_kwh) * 100, 1
        )
    
    # 5. FINANCIAL CALCULATIONS
    result.ahorro_mensual_cop = round(
        min(result.generacion_mensual_kwh, consumo_mensual_kwh) * tarifa_cop_kwh, 0
    )
    result.ahorro_anual_cop = round(result.ahorro_mensual_cop * 12, 0)
    
    # 6. SYSTEM COST WITH EQUIPMENT
    # Build cost from actual equipment prices
    costo_total_equipos = costo_paneles
    for item in inversores:
        equipo = item.get('equipo')
        cantidad = item.get('cantidad', 1)
        costo_total_equipos += float(equipo.precio_venta) * cantidad
    
    # Add other equipment (structures, cables, etc.)
    for item in selected_equipos:
        if item.get('tipo') not in ['panel', 'inversor']:
            equipo = item.get('equipo')
            cantidad = item.get('cantidad', 1)
            costo_total_equipos += float(equipo.precio_venta) * cantidad
    
    result.costo_estimado_sistema = round(costo_total_equipos, 0)
    
    # 7. INVERSER SIZING (typical 80-100% of array kWp)
    if inversores:
        potencia_inversor_kw = sum(
            item['equipo'].potencia_nominal_w * item.get('cantidad', 1) / 1000
            for item in inversores
        )
        result.inversor_potencia_kw = round(potencia_inversor_kw, 1)
    else:
        result.inversor_potencia_kw = round(potencia_pico_kwp * 0.9, 1)
    
    # 8. ROI CALCULATION (with tariff increase and degradation)
    if result.ahorro_anual_cop > 0:
        inversion = result.costo_estimado_sistema
        acumulado = 0
        for ano in range(1, vida_util_anos + 1):
            factor_tarifa = (1 + incremento_tarifa_anual / 100) ** (ano - 1)
            factor_degradacion = (1 - degradacion_anual / 100) ** (ano - 1)
            ahorro_ano = result.ahorro_anual_cop * factor_tarifa * factor_degradacion
            acumulado += ahorro_ano
            if acumulado >= inversion and result.roi_anos == 0:
                ahorro_previo = acumulado - ahorro_ano
                fraccion = (inversion - ahorro_previo) / ahorro_ano if ahorro_ano > 0 else 0
                result.roi_anos = round(ano - 1 + fraccion, 1)
        
        result.ahorro_acumulado_25_anos = round(acumulado, 0)
        if result.roi_anos == 0:
            result.roi_anos = vida_util_anos
    
    # 9. CO2 AVOIDED (Colombian grid: ~0.126 tCO2/MWh)
    result.co2_evitado_ton_ano = round(
        result.generacion_anual_kwh * 0.000126, 2
    )
    
    # 10. AREA REQUIRED
    # Approximate: modern panels ~550W with ~2.2m² area
    area_panel_m2 = 2.278 * 1.134  # ~2.58 m²
    result.area_requerida_m2 = round(numero_paneles_total * area_panel_m2 / 10, 1)
    
    return result


def get_equipment_suggestions(
    proyecto,
    resultado,
    inventario_activo,
    max_sugerencias: int = 3,
) -> Dict[str, Dict]:
    """
    Suggest suitable equipment based on sizing results.
    
    Args:
        proyecto: Proyecto instance
        resultado: EquipmentSizingResult
        inventario_activo: Queryset of active Equipo
        max_sugerencias: Max suggestions per category
    
    Returns:
        Dict with suggested equipment by type.
    """
    sugerencias = {}
    
    # Suggest panels
    paneles = inventario_activo.filter(
        categoria='panel',
        potencia_nominal_w__gte=resultado.potencia_panel_w * 0.9,
        potencia_nominal_w__lte=resultado.potencia_panel_w * 1.2,
    ).order_by('-potencia_nominal_w', 'precio_venta')[:max_sugerencias]
    
    if paneles.exists():
        panel = paneles.first()
        numero_paneles = math.ceil(resultado.potencia_pico_kwp * 1000 / panel.potencia_nominal_w)
        sugerencias['paneles'] = {
            'equipo': panel,
            'cantidad': numero_paneles,
            'costo_unitario': float(panel.precio_venta),
            'costo_total': float(panel.precio_venta) * numero_paneles,
        }
    
    # Suggest inverters
    inversor_min = resultado.inversor_potencia_kw * 1000 * 0.8
    inversor_max = resultado.inversor_potencia_kw * 1000 * 1.2
    inversores = inventario_activo.filter(
        categoria='inversor',
        potencia_nominal_w__gte=inversor_min,
        potencia_nominal_w__lte=inversor_max,
    ).order_by('potencia_nominal_w', '-eficiencia')[:max_sugerencias]
    
    if inversores.exists():
        inversor = inversores.first()
        sugerencias['inversor'] = {
            'equipo': inversor,
            'cantidad': 1,
            'costo_unitario': float(inversor.precio_venta),
            'costo_total': float(inversor.precio_venta),
        }
    
    return sugerencias
