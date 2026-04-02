"""Settings and charts admin configuration."""

from django.contrib import admin

from core.models import ChartExplanation, CompanySettings


@admin.register(CompanySettings)
class CompanySettingsAdmin(admin.ModelAdmin):
    list_display = ("name", "nit", "phone", "email")

    def has_add_permission(self, request):
        if self.model.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(ChartExplanation)
class ChartExplanationAdmin(admin.ModelAdmin):
    list_display = ("tipo_grafico", "proyecto", "titulo_corto", "es_personalizada", "fecha_actualizacion")
    list_filter = ("tipo_grafico", "es_personalizada", "fecha_actualizacion")
    search_fields = ("proyecto__nombre", "titulo_corto", "explicacion_tecnica")
    readonly_fields = ("fecha_creacion", "fecha_actualizacion")

    fieldsets = (
        ("Gráfico", {
            "fields": ("tipo_grafico", "proyecto", "es_personalizada")
        }),
        ("Contenido", {
            "fields": ("titulo_corto", "explicacion_tecnica", "puntos_clave", "recomendaciones"),
            "classes": ("wide",),
        }),
        ("Metadata", {
            "fields": ("fecha_creacion", "fecha_actualizacion"),
            "classes": ("collapse",),
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("proyecto")
