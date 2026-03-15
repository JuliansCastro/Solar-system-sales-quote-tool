"""Custom API permissions for project-scoped operations."""

from rest_framework.permissions import BasePermission


class IsProjectOwnerOrAdmin(BasePermission):
    """Allow access only to project owner (seller) or admin users."""

    message = "No tiene permisos para operar este proyecto."

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        if getattr(user, "role", None) == "admin" or getattr(user, "is_admin_role", False):
            return True

        return getattr(obj, "vendedor_id", None) == user.id
