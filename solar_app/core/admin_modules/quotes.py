"""Quote admin configuration."""

from django.contrib import admin

from core.models import Cotizacion, CotizacionItem


class CotizacionItemInline(admin.TabularInline):
    model = CotizacionItem
    extra = 1


@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = ("numero", "proyecto", "estado", "total", "fecha_emision", "creado_por")
    list_filter = ("estado", "tipo_cliente", "fecha_emision")
    search_fields = ("numero", "proyecto__nombre", "proyecto__cliente__nombre")
    readonly_fields = ("numero", "fecha_creacion", "fecha_actualizacion")
    inlines = [CotizacionItemInline]
