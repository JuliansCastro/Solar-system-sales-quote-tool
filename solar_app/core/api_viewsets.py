"""DRF ViewSets for versioned API endpoints."""

from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import IsProjectOwnerOrAdmin
from core.api_serializers import (
    EquipmentFilterQuerySerializer,
    EquipmentQuantityUpdateSerializer,
    EquipmentSelectSerializer,
    SuccessEnvelopeSerializer,
)
from core.models import Equipo, Proyecto
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


class EquipmentCatalogViewSet(viewsets.GenericViewSet):
    """List equipment catalog entries with filters."""

    permission_classes = [IsAuthenticated]
    serializer_class = EquipmentFilterQuerySerializer
    queryset = Equipo.objects.none()
    pagination_class = None
    filter_backends = []

    @extend_schema(parameters=[EquipmentFilterQuerySerializer], responses=SuccessEnvelopeSerializer)
    def list(self, request):
        serializer = EquipmentFilterQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(list_available_equipment(serializer.validated_data))


class ProjectEquipmentViewSet(viewsets.GenericViewSet):
    """Project-scoped equipment operations."""

    permission_classes = [IsAuthenticated, IsProjectOwnerOrAdmin]
    queryset = Proyecto.objects.all()
    serializer_class = SuccessEnvelopeSerializer

    def _authorize_project_access(self, request, project_id):
        project = self.get_queryset().filter(pk=project_id).first()
        if project is None:
            raise ServiceNotFoundError("Proyecto no encontrado")
        self.check_object_permissions(request, project)

    def _service_response(self, request, project_id, callable_fn):
        try:
            self._authorize_project_access(request, project_id)
            return Response(callable_fn(), status=status.HTTP_200_OK)
        except ServiceNotFoundError as exc:
            return Response(
                {"success": False, "error": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except PermissionDenied as exc:
            return Response(
                {"success": False, "error": str(exc)},
                status=status.HTTP_403_FORBIDDEN,
            )
        except ServiceValidationError as exc:
            return Response(
                {"success": False, "error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:  # pragma: no cover
            return Response(
                {"success": False, "error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"], url_path="equipment/select")
    @extend_schema(request=EquipmentSelectSerializer, responses=SuccessEnvelopeSerializer)
    def select(self, request, pk=None):
        serializer = EquipmentSelectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._service_response(
            request=request,
            project_id=pk,
            callable_fn=lambda: select_equipment(
                project_id=pk,
                payload=serializer.validated_data,
            ),
        )

    @action(
        detail=True,
        methods=["post"],
        url_path=r"equipment/(?P<selection_id>[^/.]+)/remove",
    )
    @extend_schema(
        request=None,
        parameters=[
            OpenApiParameter("selection_id", OpenApiTypes.INT, OpenApiParameter.PATH),
        ],
        responses=SuccessEnvelopeSerializer,
    )
    def remove(self, request, pk=None, selection_id=None):
        return self._service_response(
            request=request,
            project_id=pk,
            callable_fn=lambda: remove_equipment(
                project_id=pk,
                selection_id=selection_id,
            ),
        )

    @action(
        detail=True,
        methods=["post"],
        url_path=r"equipment/(?P<selection_id>[^/.]+)/update",
    )
    @extend_schema(
        request=EquipmentQuantityUpdateSerializer,
        parameters=[
            OpenApiParameter("selection_id", OpenApiTypes.INT, OpenApiParameter.PATH),
        ],
        responses=SuccessEnvelopeSerializer,
    )
    def update_qty(self, request, pk=None, selection_id=None):
        serializer = EquipmentQuantityUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._service_response(
            request=request,
            project_id=pk,
            callable_fn=lambda: update_equipment_quantity(
                project_id=pk,
                selection_id=selection_id,
                qty_change=serializer.validated_data["qty_change"],
            ),
        )

    @action(detail=True, methods=["post"], url_path="recalculate")
    @extend_schema(request=None, responses=SuccessEnvelopeSerializer)
    def recalculate(self, request, pk=None):
        return self._service_response(
            request=request,
            project_id=pk,
            callable_fn=lambda: recalculate_generation(project_id=pk),
        )

    @action(detail=True, methods=["post"], url_path="check-compatibility")
    @extend_schema(request=None, responses=SuccessEnvelopeSerializer)
    def check_compatibility(self, request, pk=None):
        return self._service_response(
            request=request,
            project_id=pk,
            callable_fn=lambda: check_compatibility(project_id=pk),
        )
