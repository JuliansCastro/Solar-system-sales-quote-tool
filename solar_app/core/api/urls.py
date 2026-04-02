"""Versioned API routes for the core app."""

from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from core.api.viewsets import EquipmentCatalogViewSet, ProjectEquipmentViewSet

router = DefaultRouter()
router.register("equipment", EquipmentCatalogViewSet, basename="v1-equipment")
router.register("projects", ProjectEquipmentViewSet, basename="v1-project-equipment")

urlpatterns = [
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
]

urlpatterns += router.urls
