# Plan de refactorizacion priorizado

## Refactor minimo viable (bajo riesgo)
PR 1: Arquitectura API v1 compatible
- Agregar capa services para negocio de selección de equipos.
- Agregar DRF ViewSets + Router en /api/v1.
- Mantener endpoints legacy como adaptadores.
- Agregar headers de deprecación y fecha sunset.

PR 2: Contratos y documentación
- Integrar drf-spectacular.
- Publicar /api/schema y /api/docs.
- Añadir guía de migración y changelog.

PR 3: Calidad y CI
- Añadir tests API v1 + contrato legacy.
- Pipeline GitHub Actions (lint, test, build, deploy-staging).
- Dependabot.

## Refactor profundo (modularización)
PR 4: Dominio por módulos
- Separar app core en submódulos: customers, projects, quotes, equipment, reporting.
- Mover queries complejas a managers/repositories.

PR 5: Seguridad y observabilidad
- JWT/OAuth2 para API externa.
- Logging JSON + Sentry + métricas Prometheus.
- Permisos por objeto en endpoints críticos.

PR 6: Escalabilidad y rendimiento
- Cache por endpoint y tuning DB.
- Pruebas de carga periódicas y presupuesto de latencia.

## Estrategia de rollout
- Feature flags:
  - API_V1_ENABLED
  - LEGACY_API_DEPRECATION_HEADERS_ENABLED
- Canary por tráfico API (10%, 50%, 100%).
- Alternativa blue-green para releases mayores.
- Rollback: volver a imagen estable previa y mantener legacy habilitado temporalmente.
