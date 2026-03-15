# Informe inicial de auditoria API

## Mapeo del proyecto
- Apps: core.
- URLs: solar_app/urls.py, core/urls.py, core/api_urls.py.
- Views tradicionales: core/views.py.
- Views API legacy: core/api_equipment.py + endpoints API en core/views.py.
- ViewSets: core/api_viewsets.py.
- Serializers: core/api_serializers.py.
- Models: core/models.py.
- Managers personalizados: no detectados.
- Services: core/services/equipment_selection_service.py.
- Tasks Celery: no detectadas.
- Scheduler de tareas: core/backup_scheduler.py (APScheduler).
- Signals: core/signals.py (placeholder).
- Middleware custom: core/middleware.py.
- Settings relevantes: solar_app/settings.py (REST_FRAMEWORK, SPECTACULAR, seguridad).
- Migrations: core/migrations/* (hasta 0013).
- Tests: core/tests.py, core/test_api_v1.py.

## Hallazgos de diagnostico
- python manage.py check: OK.
- python manage.py showmigrations: todas aplicadas.
- pytest -q: fallaba por ejecucion de test_routes.py en importacion (corregido).
- pip list --outdated: sin salida en la ejecucion actual (revisar en CI con reporte persistente).

## Puntos debiles y deuda tecnica
- API no versionada originalmente y logica de negocio acoplada a views.
- Falta de contratos OpenAPI formales antes del refactor.
- Cobertura de pruebas API limitada.
- Observabilidad de API y metricas HTTP no centralizadas.
- Autenticacion API basada en session; sin JWT/OAuth2 aun.

## Endpoints criticos
- /api/proyectos/{id}/equipment/select/
- /api/proyectos/{id}/recalculate/
- /api/pvgis/
- /api/cotizacion/{id}/charts/

## Dependencias externas
- PVGIS API.
- APScheduler.
- WeasyPrint/ReportLab/OpenPyXL para reportes.
