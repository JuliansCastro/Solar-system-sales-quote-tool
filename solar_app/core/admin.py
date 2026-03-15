"""Admin configuration for Solar Quote App."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, Cliente, Proyecto, Equipo, Cotizacion, CotizacionItem, Carga, CargaTipo, 
    CompanySettings, Departamento, Municipio, SelectedEquipo, EquipoCompatibilidad, 
    ChartExplanation
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_active')
    list_filter = ('role', 'is_active', 'is_staff')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Información adicional', {'fields': ('role', 'phone', 'company')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Información adicional', {'fields': ('role', 'phone', 'company')}),
    )


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'email', 'municipio', 'consumo_mensual_kwh', 'tarifa_electrica', 'estrato')
    list_filter = ('estrato', 'municipio__departamento', 'departamento')
    search_fields = ('nombre', 'email', 'telefono', 'municipio__nombre')


@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'cliente', 'tipo_sistema', 'estado', 'potencia_pico_kwp', 'fecha_creacion')
    list_filter = ('tipo_sistema', 'estado', 'fecha_creacion')
    search_fields = ('codigo', 'nombre', 'cliente__nombre')
    readonly_fields = ('codigo', 'fecha_creacion', 'fecha_actualizacion')


@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = ('sku', 'nombre', 'fabricante', 'categoria', 'potencia_nominal_w', 'precio_venta', 'stock', 'activo')
    list_filter = ('categoria', 'fabricante', 'sistema_compatible', 'activo')
    search_fields = ('nombre', 'modelo', 'fabricante', 'sku')
    list_editable = ('precio_venta', 'stock', 'activo')


class CotizacionItemInline(admin.TabularInline):
    model = CotizacionItem
    extra = 1


@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = ('numero', 'proyecto', 'estado', 'total', 'fecha_emision', 'creado_por')
    list_filter = ('estado', 'tipo_cliente', 'fecha_emision')
    search_fields = ('numero', 'proyecto__nombre', 'proyecto__cliente__nombre')
    readonly_fields = ('numero', 'fecha_creacion', 'fecha_actualizacion')
    inlines = [CotizacionItemInline]


@admin.register(Carga)
class CargaAdmin(admin.ModelAdmin):
    list_display = ('dispositivo', 'proyecto', 'cantidad', 'potencia_nominal_w', 'horas_uso_dia', 'prioridad')
    list_filter = ('prioridad', 'carga_reactiva')
    search_fields = ('dispositivo', 'proyecto__nombre')


@admin.register(CargaTipo)
class CargaTipoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'potencia_nominal_w', 'horas_uso_dia', 'factor_potencia', 'activo')
    list_filter = ('categoria', 'activo', 'carga_reactiva')
    search_fields = ('nombre', 'descripcion')
    list_editable = ('activo',)


@admin.register(CompanySettings)
class CompanySettingsAdmin(admin.ModelAdmin):
    list_display = ('name', 'nit', 'phone', 'email')

    def has_add_permission(self, request):
        # Only allow one instance
        if self.model.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ('id_departamento', 'nombre')
    search_fields = ('nombre',)
    ordering = ('nombre',)


@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = ('id_municipio', 'nombre', 'departamento')
    list_filter = ('departamento', 'activo')
    search_fields = ('nombre', 'departamento__nombre')
    ordering = ('departamento', 'nombre')

    def has_delete_permission(self, request, obj=None):
        return False


# ──────────────────────────────────────────────
# EQUIPMENT SELECTION ADMIN
# ──────────────────────────────────────────────

@admin.register(SelectedEquipo)
class SelectedEquipoAdmin(admin.ModelAdmin):
    list_display = ('proyecto', 'equipo', 'tipo_equipo', 'cantidad', 'activo', 'fecha_seleccion')
    list_filter = ('tipo_equipo', 'activo', 'proyecto__tipo_sistema', 'fecha_seleccion')
    search_fields = ('proyecto__nombre', 'proyecto__codigo', 'equipo__nombre', 'equipo__fabricante')
    readonly_fields = ('perdidas_estimadas_porcentaje', 'generacion_afectada_kwh', 'fecha_seleccion', 'fecha_actualizacion')
    
    fieldsets = (
        ('Información General', {
            'fields': ('proyecto', 'equipo', 'tipo_equipo', 'cantidad', 'activo')
        }),
        ('Notas', {
            'fields': ('notas',),
            'classes': ('wide',),
        }),
        ('Cálculos (Solo Lectura)', {
            'fields': ('perdidas_estimadas_porcentaje', 'generacion_afectada_kwh'),
            'classes': ('collapse',),
        }),
        ('Metadata', {
            'fields': ('fecha_seleccion', 'fecha_actualizacion'),
            'classes': ('collapse',),
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('proyecto', 'equipo')


@admin.register(EquipoCompatibilidad)
class EquipoCompatibilidadAdmin(admin.ModelAdmin):
    list_display = ('equipo_base', 'equipo_compatible', 'tipo_validacion', 'es_critico', 'activo')
    list_filter = ('tipo_validacion', 'es_critico', 'activo')
    search_fields = ('equipo_base__nombre', 'equipo_base__fabricante', 'equipo_compatible__nombre', 'equipo_compatible__fabricante')
    
    fieldsets = (
        ('Equipos', {
            'fields': ('equipo_base', 'equipo_compatible')
        }),
        ('Regla de Validación', {
            'fields': ('tipo_validacion', 'valor_minimo', 'valor_maximo', 'es_critico')
        }),
        ('Mensaje', {
            'fields': ('mensaje_alerta',),
            'classes': ('wide',),
        }),
        ('Estado', {
            'fields': ('activo',),
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('equipo_base', 'equipo_compatible')


@admin.register(ChartExplanation)
class ChartExplanationAdmin(admin.ModelAdmin):
    list_display = ('tipo_grafico', 'proyecto', 'titulo_corto', 'es_personalizada', 'fecha_actualizacion')
    list_filter = ('tipo_grafico', 'es_personalizada', 'fecha_actualizacion')
    search_fields = ('proyecto__nombre', 'titulo_corto', 'explicacion_tecnica')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')
    
    fieldsets = (
        ('Gráfico', {
            'fields': ('tipo_grafico', 'proyecto', 'es_personalizada')
        }),
        ('Contenido', {
            'fields': ('titulo_corto', 'explicacion_tecnica', 'puntos_clave', 'recomendaciones'),
            'classes': ('wide',),
        }),
        ('Metadata', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',),
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('proyecto')
