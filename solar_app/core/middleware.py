"""Custom middleware components for API lifecycle management."""

from django.conf import settings


class DeprecatedApiHeadersMiddleware:
    """Attach deprecation metadata to legacy non-versioned API routes."""

    legacy_prefixes = (
        "/api/equipment/",
        "/api/proyectos/",
        "/api/pvgis/",
        "/api/cotizacion/",
        "/api/municipios/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        path = request.path or ""

        if not getattr(settings, "LEGACY_API_DEPRECATION_HEADERS_ENABLED", True):
            return response

        if path.startswith("/api/v1/"):
            return response

        if any(path.startswith(prefix) for prefix in self.legacy_prefixes):
            response["Deprecation"] = "true"
            response["Sunset"] = "Wed, 31 Dec 2026 23:59:59 GMT"
            response["Link"] = "</api/v1/>; rel=\"successor-version\""
            response["Warning"] = '299 - "Deprecated API. Migrate to /api/v1."'
            response["X-API-Deprecated"] = "true"

        return response
