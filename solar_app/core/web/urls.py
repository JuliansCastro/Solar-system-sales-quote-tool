"""URL configuration for core app."""
from django.conf import settings
from django.urls import include, path
from . import views
from core.api import legacy_equipment as api_equipment

urlpatterns = []

if settings.API_V1_ENABLED:
    urlpatterns += [path('api/v1/', include('core.api.urls'))]

urlpatterns += [

    # Auth
    path('', views.login_view, name='home'),
    path('accounts/login/', views.login_view, name='login'),
    path('accounts/logout/', views.logout_view, name='logout'),
    path('accounts/users/', views.UserListView.as_view(), name='user_list'),
    path('accounts/users/nuevo/', views.UserCreateView.as_view(), name='user_create'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Clientes
    path('clientes/', views.ClienteListView.as_view(), name='cliente_list'),
    path('clientes/nuevo/', views.ClienteCreateView.as_view(), name='cliente_create'),
    path('clientes/<int:pk>/', views.ClienteDetailView.as_view(), name='cliente_detail'),
    path('clientes/<int:pk>/editar/', views.ClienteUpdateView.as_view(), name='cliente_update'),
    path('clientes/<int:pk>/eliminar/', views.ClienteDeleteView.as_view(), name='cliente_delete'),

    # Proyectos
    path('proyectos/', views.ProyectoListView.as_view(), name='proyecto_list'),
    path('proyectos/nuevo/', views.ProyectoCreateView.as_view(), name='proyecto_create'),
    path('proyectos/<int:pk>/', views.ProyectoDetailView.as_view(), name='proyecto_detail'),
    path('proyectos/<int:pk>/editar/', views.ProyectoUpdateView.as_view(), name='proyecto_update'),
    path('proyectos/<int:pk>/eliminar/', views.ProyectoDeleteView.as_view(), name='proyecto_delete'),
    path('proyectos/<int:pk>/cargas/', views.proyecto_cargas, name='proyecto_cargas'),
    path('proyectos/<int:pk>/dimensionar/', views.proyecto_dimensionar, name='proyecto_dimensionar'),
    path('proyectos/<int:pk>/clonar/', views.proyecto_clonar, name='proyecto_clonar'),

    # Equipos (Inventario)
    path('inventario/', views.EquipoListView.as_view(), name='equipo_list'),
    path('inventario/nuevo/', views.EquipoCreateView.as_view(), name='equipo_create'),
    path('inventario/<int:pk>/', views.EquipoDetailView.as_view(), name='equipo_detail'),
    path('inventario/<int:pk>/editar/', views.EquipoUpdateView.as_view(), name='equipo_update'),
    path('inventario/<int:pk>/eliminar/', views.EquipoDeleteView.as_view(), name='equipo_delete'),
    path('inventario/<int:pk>/clonar/', views.equipo_clonar, name='equipo_clonar'),

    # Cargas (Catálogo de tipos de carga)
    path('cargas/', views.CargaTipoListView.as_view(), name='cargatipo_list'),
    path('cargas/nuevo/', views.CargaTipoCreateView.as_view(), name='cargatipo_create'),
    path('cargas/<int:pk>/', views.CargaTipoDetailView.as_view(), name='cargatipo_detail'),
    path('cargas/<int:pk>/editar/', views.CargaTipoUpdateView.as_view(), name='cargatipo_update'),
    path('cargas/<int:pk>/clonar/', views.cargatipo_clonar, name='cargatipo_clonar'),
    path('cargas/<int:pk>/eliminar/', views.CargaTipoDeleteView.as_view(), name='cargatipo_delete'),

    # Cotizaciones
    path('cotizaciones/', views.CotizacionListView.as_view(), name='cotizacion_list'),
    path('cotizaciones/nueva/', views.CotizacionCreateView.as_view(), name='cotizacion_create'),
    path('cotizaciones/<int:pk>/', views.CotizacionDetailView.as_view(), name='cotizacion_detail'),
    path('cotizaciones/<int:pk>/editar/', views.CotizacionUpdateView.as_view(), name='cotizacion_update'),
    path('cotizaciones/<int:pk>/eliminar/', views.CotizacionDeleteView.as_view(), name='cotizacion_delete'),
    path('cotizaciones/<int:pk>/clonar/', views.cotizacion_clonar, name='cotizacion_clonar'),
    path('cotizaciones/crear-desde-proyecto/<int:pk>/', views.cotizacion_crear_desde_proyecto, name='cotizacion_crear_desde_proyecto'),

    # Reports
    path('cotizaciones/<int:pk>/pdf/', views.cotizacion_pdf, name='cotizacion_pdf'),
    path('cotizaciones/<int:pk>/pdf-weasy/', views.cotizacion_pdf_weasyprint, name='cotizacion_pdf_weasy'),
    path('cotizaciones/<int:pk>/excel/', views.cotizacion_excel, name='cotizacion_excel'),

    # Settings
    path('configuracion/', views.company_settings_view, name='company_settings'),
    path('configuracion/backup-restore/', views.BackupRestoreView.as_view(), name='backup_restore'),

    # API endpoints
    path('api/pvgis/', views.api_pvgis, name='api_pvgis'),
    path('api/cotizacion/<int:pk>/charts/', views.cotizacion_charts_data, name='cotizacion_charts_data'),
    path('api/municipios/<int:departamento_id>/', views.api_municipios_por_departamento, name='api_municipios_por_departamento'),
    
    # Equipment Selection API endpoints
    path('api/equipment/list/', api_equipment.api_equipment_list, name='api_equipment_list'),
    path('api/proyectos/<int:pk>/equipment/select/', api_equipment.api_equipment_select, name='api_equipment_select'),
    path('api/proyectos/<int:pk>/equipment/<int:seleccion_id>/remove/', api_equipment.api_equipment_remove, name='api_equipment_remove'),
    path('api/proyectos/<int:pk>/equipment/<int:seleccion_id>/update/', api_equipment.api_equipment_update_qty, name='api_equipment_update_qty'),
    path('api/proyectos/<int:pk>/recalculate/', api_equipment.api_recalculate_generation, name='api_recalculate'),
    path('api/proyectos/<int:pk>/check-compatibility/', api_equipment.api_check_compatibility, name='api_check_compatibility'),
]
