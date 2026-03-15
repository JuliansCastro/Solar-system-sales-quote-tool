from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test.utils import override_settings
from rest_framework.test import APIClient

from core.models import Cliente, Departamento, Equipo, Municipio, Proyecto


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class EquipmentApiV1TestCase(TestCase):
    def setUp(self):
        self.api_client = APIClient()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="api-user",
            password="testpass123",
            role="admin",
        )
        self.api_client.force_authenticate(self.user)
        self.seller_user = user_model.objects.create_user(
            username="seller-user",
            password="testpass123",
            role="seller",
        )

        self.departamento, _ = Departamento.objects.get_or_create(
            id_departamento=11,
            defaults={"nombre": "Bogota"},
        )
        self.municipio, _ = Municipio.objects.get_or_create(
            id_municipio=11001,
            defaults={
                "nombre": "Bogota",
                "departamento": self.departamento,
                "activo": True,
            },
        )
        self.cliente = Cliente.objects.create(
            nombre="Cliente API",
            email="cliente@example.com",
            telefono="3000000000",
            direccion="Calle 123",
            departamento=self.departamento,
            municipio=self.municipio,
            consumo_mensual_kwh=450,
            tarifa_electrica=800,
            creado_por=self.user,
        )
        self.proyecto = Proyecto.objects.create(
            nombre="Proyecto API",
            cliente=self.cliente,
            vendedor=self.user,
        )
        self.equipo = Equipo.objects.create(
            nombre="Panel Solar",
            modelo="PS-450",
            fabricante="SolarTech",
            categoria="panel",
            sku="PANEL-450-API",
            potencia_nominal_w=450,
            sistema_compatible="ambos",
            precio_proveedor=Decimal("400000"),
            precio_venta=Decimal("520000"),
            stock=10,
            activo=True,
        )

    def test_v1_list_equipment(self):
        response = self.api_client.get("/api/v1/equipment/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertGreaterEqual(response.data["count"], 1)

    def test_v1_select_equipment(self):
        payload = {
            "equipo_id": self.equipo.id,
            "tipo_equipo": "panel",
            "cantidad": 2,
        }
        response = self.api_client.post(
            f"/api/v1/projects/{self.proyecto.id}/equipment/select/",
            payload,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["selected_equipo"]["cantidad"], 2)

    def test_legacy_endpoint_has_deprecation_headers(self):
        self.client.force_login(self.user)
        response = self.client.get("/api/equipment/list/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Deprecation"], "true")
        self.assertIn("/api/v1/", response["Link"])

    def test_legacy_contract_shape_for_select(self):
        self.client.force_login(self.user)
        response = self.client.post(
            f"/api/proyectos/{self.proyecto.id}/equipment/select/",
            data={
                "equipo_id": self.equipo.id,
                "tipo_equipo": "panel",
                "cantidad": 1,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("success", payload)
        self.assertIn("selected_equipo", payload)
        self.assertIn("message", payload)

    def test_jwt_token_obtain_pair(self):
        anonymous_client = APIClient()
        response = anonymous_client.post(
            "/api/v1/auth/token/",
            {"username": "api-user", "password": "testpass123"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_v1_project_operations_require_project_permission(self):
        forbidden_client = APIClient()
        forbidden_client.force_authenticate(self.seller_user)
        response = forbidden_client.post(
            f"/api/v1/projects/{self.proyecto.id}/equipment/select/",
            {
                "equipo_id": self.equipo.id,
                "tipo_equipo": "panel",
                "cantidad": 1,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.data["success"])

    def test_metrics_endpoint_available(self):
        response = self.client.get("/metrics")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "django_http_responses_total")
