# Deprecated Scripts Policy

- Deprecation date: 2026-03-15
- Planned removal date: 2026-06-30
- Soft-delete location: `deprecated/`

Moved scripts:

- `deprecated/scripts/run_load_equipment.py`
- `deprecated/scripts/setup_test_data.py`
- `deprecated/scripts/0012_load_departamentos_municipios.py`
- `deprecated/solar_app/load_equipment.py`
- `deprecated/solar_app/add_equipment_list.py`

Operational replacements:

- `python manage.py load_equipment_catalog`
- `python manage.py setup_demo_data`
