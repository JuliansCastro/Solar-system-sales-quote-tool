"""Legacy API adapters for backward-compatible equipment endpoints."""

import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from core.api.serializers import (
    EquipmentFilterQuerySerializer,
    EquipmentQuantityUpdateSerializer,
    EquipmentSelectSerializer,
)
from core.services.equipment_selection_service import (
    ServiceNotFoundError,
    ServiceValidationError,
    check_compatibility,
    list_available_equipment,
    recalculate_generation,
    remove_equipment,
    select_equipment,
    update_equipment_quantity,
)


def _legacy_response(payload, status=200):
    response = JsonResponse(payload, status=status)
    response["Deprecation"] = "true"
    response["Sunset"] = "Wed, 31 Dec 2026 23:59:59 GMT"
    response["Link"] = "</api/v1/>; rel=\"successor-version\""
    response["Warning"] = '299 - "Deprecated API. Migrate to /api/v1."'
    response["X-API-Deprecated"] = "true"
    return response


def _call_service(service_fn):
    try:
        return _legacy_response(service_fn())
    except ServiceNotFoundError as exc:
        return _legacy_response({"success": False, "error": str(exc)}, status=404)
    except ServiceValidationError as exc:
        return _legacy_response({"success": False, "error": str(exc)}, status=400)
    except Exception as exc:  # pragma: no cover
        return _legacy_response({"success": False, "error": str(exc)}, status=400)


@login_required
@require_http_methods(["GET"])
def api_equipment_list(request):
    serializer = EquipmentFilterQuerySerializer(data=request.GET)
    if not serializer.is_valid():
        return _legacy_response({"success": False, "error": serializer.errors}, status=400)
    return _call_service(lambda: list_available_equipment(serializer.validated_data))


@login_required
@require_http_methods(["POST"])
def api_equipment_select(request, pk):
    data = json.loads(request.body or "{}")
    serializer = EquipmentSelectSerializer(data=data)
    if not serializer.is_valid():
        return _legacy_response({"success": False, "error": serializer.errors}, status=400)
    return _call_service(lambda: select_equipment(pk, serializer.validated_data))


@login_required
@require_http_methods(["POST"])
def api_equipment_remove(request, pk, seleccion_id):
    return _call_service(lambda: remove_equipment(pk, seleccion_id))


@login_required
@require_http_methods(["POST"])
def api_equipment_update_qty(request, pk, seleccion_id):
    data = json.loads(request.body or "{}")
    serializer = EquipmentQuantityUpdateSerializer(data=data)
    if not serializer.is_valid():
        return _legacy_response({"success": False, "error": serializer.errors}, status=400)
    return _call_service(
        lambda: update_equipment_quantity(pk, seleccion_id, serializer.validated_data["qty_change"])
    )


@login_required
@require_http_methods(["POST"])
def api_recalculate_generation(request, pk):
    return _call_service(lambda: recalculate_generation(pk))


@login_required
@require_http_methods(["POST"])
def api_check_compatibility(request, pk):
    return _call_service(lambda: check_compatibility(pk))
