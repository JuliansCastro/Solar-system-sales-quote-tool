from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction

from core.models import Cliente, Departamento, Equipo, Municipio, Proyecto
from core.services.equipment_catalog_seed import seed_equipment_catalog


@transaction.atomic
def seed_demo_data(
    *,
    admin_username: str = "admin",
    admin_password: str = "admin123",
    admin_email: str = "admin@test.com",
) -> dict[str, Any]:
    user_model = get_user_model()

    admin_user, admin_created = user_model.objects.get_or_create(
        username=admin_username,
        defaults={
            "email": admin_email,
            "role": user_model.Role.ADMIN,
            "is_staff": True,
            "is_superuser": True,
        },
    )
    if admin_created:
        admin_user.set_password(admin_password)
        admin_user.save(update_fields=["password"])

    departamento = Departamento.objects.first()
    if not departamento:
        raise ValueError(
            "No active Departamento found. Run migrations/data load first."
        )

    municipio = Municipio.objects.filter(departamento=departamento, activo=True).first()
    if not municipio:
        raise ValueError("No active Municipio found for selected Departamento.")

    cliente, cliente_created = Cliente.objects.get_or_create(
        nombre="Cliente Test",
        defaults={
            "email": "cliente@test.com",
            "telefono": "3001234567",
            "direccion": "Calle 123 #456",
            "departamento": departamento,
            "municipio": municipio,
            "consumo_mensual_kwh": 500,
            "tarifa_electrica": 700,
            "estrato": 3,
            "creado_por": admin_user,
        },
    )

    proyecto, proyecto_created = Proyecto.objects.get_or_create(
        codigo="TEST-2603-0001",
        defaults={
            "nombre": "Proyecto Test",
            "cliente": cliente,
            "vendedor": admin_user,
            "tipo_sistema": Proyecto.TipoSistema.ON_GRID,
            "estado": Proyecto.Estado.EN_DISENO,
            "latitud": 4.711,
            "longitud": -74.0721,
            "direccion_instalacion": "Calle 123 #456",
            "hsp_promedio": 4.5,
        },
    )

    equipment_summary = seed_equipment_catalog(default_stock=50, mark_active=True)

    return {
        "admin_created": admin_created,
        "cliente_created": cliente_created,
        "proyecto_created": proyecto_created,
        "equipment": equipment_summary,
        "departamento": departamento.nombre,
        "municipio": municipio.nombre,
        "total_equipos": Equipo.objects.count(),
    }
