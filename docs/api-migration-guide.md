# Guia de migracion API

## Objetivo
Migrar de endpoints legacy sin version (/api/...) a endpoints versionados (/api/v1/...) manteniendo compatibilidad.

## Endpoints nuevos (v1)
- GET /api/v1/equipment/
- POST /api/v1/projects/{id}/equipment/select/
- POST /api/v1/projects/{id}/equipment/{selection_id}/remove/
- POST /api/v1/projects/{id}/equipment/{selection_id}/update/
- POST /api/v1/projects/{id}/recalculate/
- POST /api/v1/projects/{id}/check-compatibility/

## Compatibilidad hacia atras
Los endpoints legacy siguen activos y devuelven headers:
- Deprecation: true
- Sunset: Wed, 31 Dec 2026 23:59:59 GMT
- Link: </api/v1/>; rel="successor-version"

## Plan recomendado para clientes
1. Consumir OpenAPI en /api/schema/.
2. Cambiar base path a /api/v1.
3. Probar contrato de respuestas en staging.
4. Desactivar uso legacy antes de la fecha de sunset.
