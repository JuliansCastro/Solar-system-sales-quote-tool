# Core Script Memory (Single Source)

## Current Operational Entry Points

- Equipment catalog seed: `python manage.py load_equipment_catalog`
- Demo data seed: `python manage.py setup_demo_data`
- Backup operations: `python manage.py backup_db`, `python manage.py restore_db`
- Scheduler control: `python manage.py manage_scheduler`

## Critical Components (Do Not Break)

- Data migration path depends on `solar_app/core/migrations/0012_load_departamentos_municipios.py`.
- Runtime backup flow depends on `solar_app/core/backup_scheduler.py` and backup/restore commands.
- Restore drill can be destructive in the wrong database/environment.

## Refactor Outcome (What Was Consolidated)

- Legacy equipment/demo scripts were consolidated into services and management commands:
	- `core/services/equipment_catalog_seed.py`
	- `core/services/demo_data_seed.py`
	- `core/management/commands/load_equipment_catalog.py`
	- `core/management/commands/setup_demo_data.py`

## Repository Policy

- No active code should import from `deprecated` paths.
- Use command entrypoints and service modules above as the supported path.

## Minimal Validation Before Release

- `python manage.py check`
- `python manage.py showmigrations`
- `pytest -q`
- `python scripts/validate_no_deprecated_imports.py`
