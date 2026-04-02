from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings

from core.models import Cliente, Equipo, Proyecto
from core.services.equipment_catalog_seed import DEFAULT_EQUIPMENT_CATALOG


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class EquipmentCatalogCommandTests(TestCase):
    def test_load_equipment_catalog_is_idempotent(self):
        call_command("load_equipment_catalog")
        first_count = Equipo.objects.count()

        call_command("load_equipment_catalog")
        second_count = Equipo.objects.count()

        self.assertEqual(first_count, len(DEFAULT_EQUIPMENT_CATALOG))
        self.assertEqual(second_count, len(DEFAULT_EQUIPMENT_CATALOG))

    def test_setup_demo_data_creates_expected_records(self):
        call_command("setup_demo_data")

        user_model = get_user_model()
        self.assertTrue(user_model.objects.filter(username="admin").exists())
        self.assertTrue(Cliente.objects.filter(nombre="Cliente Test").exists())
        self.assertTrue(Proyecto.objects.filter(codigo="TEST-2603-0001").exists())
        self.assertGreaterEqual(Equipo.objects.count(), len(DEFAULT_EQUIPMENT_CATALOG))
