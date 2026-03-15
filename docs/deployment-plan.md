# Plan de despliegue y rollback

## Estrategia de rollout
- Fase 1 (staging): desplegar API v1 y mantener legacy activo.
- Fase 2 (canary): enrutar 10-20% de trafico API al backend nuevo.
- Fase 3 (general): 100% trafico con monitoreo reforzado y headers de deprecacion legacy.

## Feature flags
- API_V1_ENABLED (default true en staging/prod).
- LEGACY_API_DEPRECATION_HEADERS_ENABLED (default true).

## Verificaciones previas
1. python manage.py check
2. python manage.py migrate --plan
3. python -m pytest -q
4. ruff check . && black --check . && isort --check-only .

## Rollback
1. Revertir despliegue a imagen previa estable.
2. Mantener base de datos sin rollback de schema destructivo.
3. Rehabilitar solo rutas legacy temporalmente si aplica.
4. Validar salud con python manage.py check y pruebas smoke.
