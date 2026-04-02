"""Equipment admin configuration."""

from django.contrib import admin

from core.models import Equipo, EquipoCompatibilidad, SelectedEquipo


@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = ("sku", "nombre", "fabricante", "categoria", "potencia_nominal_w", "precio_venta", "stock", "activo")
    list_filter = ("categoria", "fabricante", "sistema_compatible", "activo")
    search_fields = ("nombre", "modelo", "fabricante", "sku")
    list_editable = ("precio_venta", "stock", "activo")


@admin.register(SelectedEquipo)
class SelectedEquipoAdmin(admin.ModelAdmin):
    list_display = ("proyecto", "equipo", "tipo_equipo", "cantidad", "activo", "fecha_seleccion")
    list_filter = ("tipo_equipo", "activo", "proyecto__tipo_sistema", "fecha_seleccion")
    search_fields = ("proyecto__nombre", "proyecto__codigo", "equipo__nombre", "equipo__fabricante")
    readonly_fields = ("perdidas_estimadas_porcentaje", "generacion_afectada_kwh", "fecha_seleccion", "fecha_actualizacion")

    fieldsets = (
        ("Información General", {
            "fields": ("proyecto", "equipo", "tipo_equipo", "cantidad", "activo")
        }),
        ("Notas", {
            "fields": ("notas",),
            "classes": ("wide",),
        }),
        ("Cálculos (Solo Lectura)", {
            "fields": ("perdidas_estimadas_porcentaje", "generacion_afectada_kwh"),
            "classes": ("collapse",),
        }),
        ("Metadata", {
            "fields": ("fecha_seleccion", "fecha_actualizacion"),
            "classes": ("collapse",),
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("proyecto", "equipo")


@admin.register(EquipoCompatibilidad)
class EquipoCompatibilidadAdmin(admin.ModelAdmin):
    list_display = ("equipo_base", "equipo_compatible", "tipo_validacion", "es_critico", "activo")
    list_filter = ("tipo_validacion", "es_critico", "activo")
    search_fields = ("equipo_base__nombre", "equipo_base__fabricante", "equipo_compatible__nombre", "equipo_compatible__fabricante")

    fieldsets = (
        ("Equipos", {
            "fields": ("equipo_base", "equipo_compatible")
        }),
        ("Regla de Validación", {
            "fields": ("tipo_validacion", "valor_minimo", "valor_maximo", "es_critico")
        }),
        ("Mensaje", {
            "fields": ("mensaje_alerta",),
            "classes": ("wide",),
        }),
        ("Estado", {
            "fields": ("activo",),
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("equipo_base", "equipo_compatible")
