"""Project and load admin configuration."""

from django.contrib import admin

from core.models import Carga, CargaTipo, Proyecto


@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "cliente", "tipo_sistema", "estado", "potencia_pico_kwp", "fecha_creacion")
    list_filter = ("tipo_sistema", "estado", "fecha_creacion")
    search_fields = ("codigo", "nombre", "cliente__nombre")
    readonly_fields = ("codigo", "fecha_creacion", "fecha_actualizacion")


@admin.register(Carga)
class CargaAdmin(admin.ModelAdmin):
    list_display = ("dispositivo", "proyecto", "cantidad", "potencia_nominal_w", "horas_uso_dia", "prioridad")
    list_filter = ("prioridad", "carga_reactiva")
    search_fields = ("dispositivo", "proyecto__nombre")


@admin.register(CargaTipo)
class CargaTipoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "potencia_nominal_w", "horas_uso_dia", "factor_potencia", "activo")
    list_filter = ("categoria", "activo", "carga_reactiva")
    search_fields = ("nombre", "descripcion")
    list_editable = ("activo",)
