# Changelog

## 2026-03-15

### Added
- API versionada en /api/v1 con DRF ViewSets y Router.
- OpenAPI con drf-spectacular: /api/schema/ y /api/docs/.
- Capa de servicios para seleccion de equipos.
- Servicio de seed de catalogo en core/services/equipment_catalog_seed.py.
- Servicio de datos demo en core/services/demo_data_seed.py.
- Comandos manage.py load_equipment_catalog y manage.py setup_demo_data.
- Middleware de headers de deprecacion para endpoints legacy.
- Tests de integracion y contrato basico para API v1 y legacy.
- Pipeline CI de GitHub Actions (lint, test, build, deploy-staging).
- Gate en CI para bloquear imports/referencias a scripts deprecados.
- Job integration-checks en CI para validar scheduler/comandos de backup y carga de datos.
- Dependabot para pip y GitHub Actions.
- Script de benchmark basico para P95/P99.
- JWT en API v1 con endpoints de token, refresh y verify.
- Permisos por objeto para operaciones de equipos por proyecto (admin/superuser o vendedor asignado).
- Observabilidad con logs JSON estructurados, integracion opcional con Sentry y endpoint /metrics (Prometheus).
- Feature flags de rollout: API_V1_ENABLED y LEGACY_API_DEPRECATION_HEADERS_ENABLED.

### Changed
- Endpoints legacy de equipment ahora funcionan como adaptadores hacia la capa de servicios.
- test_routes.py ya no interfiere con pytest en importacion.
- Scripts redundantes de carga fueron movidos a deprecated/ para soft-delete.
- El pipeline de tests en CI ahora exige cobertura minima de 70% sobre core.
