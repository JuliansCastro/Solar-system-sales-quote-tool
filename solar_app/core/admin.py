"""Admin configuration for Solar Quote App."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Cliente, Proyecto, Equipo, Cotizacion, CotizacionItem, Carga, CargaTipo, CompanySettings


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
    list_display = ('nombre', 'email', 'ciudad', 'consumo_mensual_kwh', 'tarifa_electrica', 'estrato')
    list_filter = ('estrato', 'ciudad', 'departamento')
    search_fields = ('nombre', 'email', 'telefono', 'ciudad')


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

    def has_delete_permission(self, request, obj=None):
        return False
