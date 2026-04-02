"""Customer and geography admin configuration."""

from django.contrib import admin

from core.models import Cliente, Departamento, Municipio


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "email", "municipio", "consumo_mensual_kwh", "tarifa_electrica", "estrato")
    list_filter = ("estrato", "municipio__departamento", "departamento")
    search_fields = ("nombre", "email", "telefono", "municipio__nombre")


@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ("id_departamento", "nombre")
    search_fields = ("nombre",)
    ordering = ("nombre",)


@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = ("id_municipio", "nombre", "departamento")
    list_filter = ("departamento", "activo")
    search_fields = ("nombre", "departamento__nombre")
    ordering = ("departamento", "nombre")

    def has_delete_permission(self, request, obj=None):
        return False
