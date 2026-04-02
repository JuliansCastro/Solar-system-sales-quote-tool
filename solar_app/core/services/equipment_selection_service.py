"""Service layer for equipment selection and sizing API operations."""

from django.db.models import Q

from core.calculations.equipment_sizing import (
    calculate_generation_with_equipment,
    validate_equipment_compatibility,
)
from core.web.forms import EquipoFilterFormForSelection
from core.models import Equipo, EquipoCompatibilidad, Proyecto, SelectedEquipo


class ServiceValidationError(Exception):
    """Raised when request input fails business rules."""


class ServiceNotFoundError(Exception):
    """Raised when a required domain entity does not exist."""


def _get_project(project_id):
    try:
        return Proyecto.objects.select_related("cliente").get(pk=project_id)
    except Proyecto.DoesNotExist as exc:
        raise ServiceNotFoundError("Proyecto no encontrado") from exc


def _get_active_equipo(equipo_id):
    try:
        return Equipo.objects.get(pk=equipo_id, activo=True)
    except Equipo.DoesNotExist as exc:
        raise ServiceNotFoundError("Equipo no encontrado") from exc


def _serialize_selected_equipo(selected):
    return {
        "id": selected.id,
        "equipo_id": selected.equipo_id,
        "nombre": f"{selected.equipo.fabricante} {selected.equipo.modelo}",
        "tipo": selected.tipo_equipo,
        "cantidad": selected.cantidad,
        "notas": selected.notas,
        "precio_unitario": float(selected.equipo.precio_venta),
        "subtotal": selected.subtotal_equipo,
    }


def list_available_equipment(filters):
    """Return filtered active equipment list with bounded result size."""
    form = EquipoFilterFormForSelection(filters)
    qs = Equipo.objects.filter(activo=True)

    if form.is_valid():
        cleaned = form.cleaned_data
        if cleaned.get("categoria_equipo"):
            qs = qs.filter(categoria=cleaned["categoria_equipo"])
        if cleaned.get("fabricante"):
            qs = qs.filter(fabricante__icontains=cleaned["fabricante"])
        if cleaned.get("potencia_min"):
            qs = qs.filter(potencia_nominal_w__gte=cleaned["potencia_min"])
        if cleaned.get("potencia_max"):
            qs = qs.filter(potencia_nominal_w__lte=cleaned["potencia_max"])
        if cleaned.get("en_stock"):
            qs = qs.filter(stock__gt=0)
        if cleaned.get("buscar"):
            search = cleaned["buscar"]
            qs = qs.filter(
                Q(nombre__icontains=search)
                | Q(modelo__icontains=search)
                | Q(sku__icontains=search)
                | Q(fabricante__icontains=search)
            )

    equipos = qs.order_by("-stock", "precio_venta")[:100]
    data = [
        {
            "id": eq.id,
            "nombre": f"{eq.fabricante} {eq.modelo}",
            "potencia_w": eq.potencia_nominal_w,
            "eficiencia": eq.eficiencia or 0,
            "precio": float(eq.precio_venta),
            "stock": eq.stock,
            "en_stock": eq.stock > 0,
            "categoria": eq.categoria,
            "voltaje": eq.voltaje_nominal,
            "corriente": eq.corriente_nominal,
        }
        for eq in equipos
    ]
    return {"success": True, "count": len(data), "equipos": data}


def select_equipment(project_id, payload):
    """Create or update selected equipment for a project."""
    proyecto = _get_project(project_id)
    equipo = _get_active_equipo(payload["equipo_id"])
    cantidad = payload.get("cantidad", 1)

    if cantidad < 1:
        raise ServiceValidationError("La cantidad debe ser mayor a 0")
    if equipo.stock < cantidad:
        raise ServiceValidationError(f"Stock insuficiente. Disponibles: {equipo.stock}")

    selected, created = SelectedEquipo.objects.update_or_create(
        proyecto=proyecto,
        equipo=equipo,
        tipo_equipo=payload["tipo_equipo"],
        defaults={
            "cantidad": cantidad,
            "notas": payload.get("notas", ""),
            "activo": True,
        },
    )

    return {
        "success": True,
        "created": created,
        "message": f"{'Equipo agregado' if created else 'Equipo actualizado'} exitosamente",
        "selected_equipo": _serialize_selected_equipo(selected),
    }


def list_selected_equipment(project_id):
    """Return selected equipment collection for a project resource."""
    proyecto = _get_project(project_id)
    selected_list = SelectedEquipo.objects.filter(
        proyecto=proyecto,
        activo=True,
    ).select_related("equipo")

    items = [_serialize_selected_equipo(sel) for sel in selected_list]
    return {
        "success": True,
        "count": len(items),
        "items": items,
    }


def update_selected_equipment(project_id, selection_id, payload):
    """Patch a selected equipment resource in a project."""
    proyecto = _get_project(project_id)
    try:
        selected = SelectedEquipo.objects.select_related("equipo").get(
            pk=selection_id,
            proyecto=proyecto,
            activo=True,
        )
    except SelectedEquipo.DoesNotExist as exc:
        raise ServiceNotFoundError("Equipo seleccionado no encontrado") from exc

    if "cantidad" in payload:
        nueva_cantidad = payload["cantidad"]
        if selected.equipo.stock < nueva_cantidad:
            raise ServiceValidationError(
                f"Stock insuficiente. Disponibles: {selected.equipo.stock}"
            )
        selected.cantidad = nueva_cantidad

    if "notas" in payload:
        selected.notas = payload["notas"]

    selected.save(update_fields=["cantidad", "notas", "fecha_actualizacion"])
    return {
        "success": True,
        "message": "Equipo seleccionado actualizado",
        "selected_equipo": _serialize_selected_equipo(selected),
    }


def remove_equipment(project_id, selection_id):
    """Remove one selected equipment row from a project."""
    proyecto = _get_project(project_id)
    try:
        selected = SelectedEquipo.objects.select_related("equipo").get(
            pk=selection_id,
            proyecto=proyecto,
        )
    except SelectedEquipo.DoesNotExist as exc:
        raise ServiceNotFoundError("Equipo seleccionado no encontrado") from exc

    equipo_nombre = f"{selected.equipo.fabricante} {selected.equipo.modelo}"
    selected.delete()
    return {"success": True, "message": f"{equipo_nombre} removido exitosamente"}


def update_equipment_quantity(project_id, selection_id, qty_change):
    """Increment/decrement selected equipment quantity safely."""
    proyecto = _get_project(project_id)
    try:
        selected = SelectedEquipo.objects.select_related("equipo").get(
            pk=selection_id,
            proyecto=proyecto,
        )
    except SelectedEquipo.DoesNotExist as exc:
        raise ServiceNotFoundError("Equipo seleccionado no encontrado") from exc

    if qty_change == 0:
        raise ServiceValidationError("No se puede cambiar la cantidad en 0")

    nueva_cantidad = selected.cantidad + qty_change
    if nueva_cantidad < 1:
        raise ServiceValidationError("La cantidad debe ser mayor a 0")
    if nueva_cantidad > selected.equipo.stock:
        raise ServiceValidationError(
            f"Stock insuficiente. Disponibles: {selected.equipo.stock}"
        )

    selected.cantidad = nueva_cantidad
    selected.save(update_fields=["cantidad", "fecha_actualizacion"])
    return {
        "success": True,
        "message": f"Cantidad actualizada a {nueva_cantidad}",
        "nueva_cantidad": nueva_cantidad,
    }


def recalculate_generation(project_id):
    """Recalculate sizing results from currently selected equipment."""
    proyecto = _get_project(project_id)
    cliente = proyecto.cliente

    selected_list = SelectedEquipo.objects.filter(
        proyecto=proyecto,
        activo=True,
    ).select_related("equipo")

    if not selected_list.exists():
        raise ServiceValidationError("No hay equipos seleccionados para calcular")

    equipos_para_calcular = [
        {
            "tipo": sel.tipo_equipo,
            "equipo": sel.equipo,
            "cantidad": sel.cantidad,
            "notas": sel.notas,
        }
        for sel in selected_list
    ]

    resultado = calculate_generation_with_equipment(
        selected_equipos=equipos_para_calcular,
        consumo_mensual_kwh=proyecto.consumo_mensual_efectivo_kwh,
        hsp=proyecto.hsp_promedio,
        tarifa_cop_kwh=cliente.tarifa_electrica,
        tipo_sistema=proyecto.tipo_sistema,
    )

    compatibility_rules = EquipoCompatibilidad.objects.filter(activo=True)
    is_compatible, issues = validate_equipment_compatibility(
        equipos_para_calcular,
        list(compatibility_rules),
    )

    alertas = []
    if resultado.alertas:
        alertas.extend(resultado.alertas)

    for issue in issues:
        alertas.append(
            {
                "tipo": "critico" if issue.es_critico else "advertencia",
                "mensaje": issue.mensaje,
                "parametro": issue.parametro_afectado,
            }
        )

    return {
        "success": True,
        "resultado": {
            "potencia_pico_kwp": resultado.potencia_pico_kwp,
            "numero_paneles": resultado.numero_paneles,
            "generacion_mensual_kwh": resultado.generacion_mensual_kwh,
            "generacion_anual_kwh": resultado.generacion_anual_kwh,
            "porcentaje_cobertura": resultado.porcentaje_cobertura,
            "ahorro_mensual_cop": resultado.ahorro_mensual_cop,
            "ahorro_anual_cop": resultado.ahorro_anual_cop,
            "costo_estimado_sistema": resultado.costo_estimado_sistema,
            "roi_anos": resultado.roi_anos,
            "ahorro_acumulado_25_anos": resultado.ahorro_acumulado_25_anos,
            "co2_evitado_ton_ano": resultado.co2_evitado_ton_ano,
            "inversor_potencia_kw": resultado.inversor_potencia_kw,
            "area_requerida_m2": resultado.area_requerida_m2,
            "perdidas_totales_porcentaje": round(resultado.perdidas_totales_porcentaje, 2),
            "perdidas_paneles_porcentaje": round(resultado.perdidas_paneles_porcentaje, 2),
            "perdidas_inversor_porcentaje": round(resultado.perdidas_inversor_porcentaje, 2),
        },
        "compatible": is_compatible,
        "alertas": alertas,
        "equipos_seleccionados": [
            _serialize_selected_equipo(sel)
            for sel in selected_list
        ],
    }


def check_compatibility(project_id):
    """Validate compatibility for selected equipment in a project."""
    proyecto = _get_project(project_id)

    selected_list = SelectedEquipo.objects.filter(
        proyecto=proyecto,
        activo=True,
    ).select_related("equipo")

    equipos_para_validar = [
        {
            "tipo": sel.tipo_equipo,
            "equipo": sel.equipo,
            "cantidad": sel.cantidad,
        }
        for sel in selected_list
    ]

    compatibility_rules = EquipoCompatibilidad.objects.filter(activo=True)
    is_compatible, issues = validate_equipment_compatibility(
        equipos_para_validar,
        list(compatibility_rules),
    )

    return {
        "success": True,
        "compatible": is_compatible,
        "issues": [
            {
                "es_critico": issue.es_critico,
                "equipo1": issue.equipo1_nombre,
                "equipo2": issue.equipo2_nombre,
                "tipo_validacion": issue.tipo_validacion,
                "mensaje": issue.mensaje,
                "parametro": issue.parametro_afectado,
            }
            for issue in issues
        ],
    }
