"""
Views for Solar Quote App.

Organized by section:
- Authentication
- Dashboard
- Cliente CRUD
- Proyecto CRUD + Sizing
- Equipo (Inventory) CRUD
- Cotización CRUD
- Reports
"""

import json
import gzip
import shutil
import tempfile
import os
import hashlib
import logging
import base64
from pathlib import Path
from io import BytesIO

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView,
)
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum, Count
from django.db import connections
from django.conf import settings
from django.utils import timezone
from django.template.loader import render_to_string

from weasyprint import HTML

from core.models import (
    User, Cliente, Proyecto, Equipo, Cotizacion, CotizacionItem, Carga, CargaTipo,
    CompanySettings, Departamento, Municipio, SelectedEquipo, Archivo,
)
from .forms import (
    CustomLoginForm, UserRegistrationForm,
    ClienteForm, ProyectoForm, EquipoForm, EquipoFilterForm,
    CotizacionForm, CotizacionItemFormSet, CargaForm, CargaFormSet,
    CargaTipoForm, CompanySettingsForm, BackupRestoreForm,
)
from core.calculations.sizing import (
    dimensionar_on_grid, dimensionar_off_grid, obtener_datos_pvgis,
    sugerir_equipos, calcular_proyeccion_financiera,
)
from core.calculations.chart_data import build_cotizacion_charts_payload, _calculate_sizing_from_items
from core.calculations.equipment_sizing import calculate_generation_with_equipment
from core.calculations.chart_data import build_cotizacion_charts_payload

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# MIXINS
# ──────────────────────────────────────────────

class AdminRequiredMixin(LoginRequiredMixin):
    """Require admin role."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_admin_role and not request.user.is_superuser:
            messages.error(request, 'No tienes permisos de administrador.')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)


class SuperuserRequiredMixin(LoginRequiredMixin):
    """Require superuser permissions."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_superuser:
            messages.error(request, 'No tienes permisos de superusuario.')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)


# ──────────────────────────────────────────────
# AUTHENTICATION VIEWS
# ──────────────────────────────────────────────

def login_view(request):
    """User login."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'¡Bienvenido, {user.get_full_name() or user.username}!')
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
    else:
        form = CustomLoginForm()

    return render(request, 'core/auth/login.html', {'form': form})


def logout_view(request):
    """User logout."""
    logout(request)
    messages.info(request, 'Sesión cerrada correctamente.')
    return redirect('login')


class UserCreateView(AdminRequiredMixin, CreateView):
    """Create new user (admin only)."""
    model = User
    form_class = UserRegistrationForm
    template_name = 'core/auth/user_form.html'
    success_url = reverse_lazy('user_list')

    def form_valid(self, form):
        messages.success(self.request, 'Usuario creado exitosamente.')
        return super().form_valid(form)


class UserListView(AdminRequiredMixin, ListView):
    """List all users (admin only)."""
    model = User
    template_name = 'core/auth/user_list.html'
    context_object_name = 'users'


# ──────────────────────────────────────────────
# DASHBOARD
# ──────────────────────────────────────────────

@login_required
def dashboard(request):
    """Main dashboard for sellers."""
    user = request.user

    # Stats
    if user.is_admin_role or user.is_superuser:
        proyectos = Proyecto.objects.all()
        clientes = Cliente.objects.all()
        cotizaciones = Cotizacion.objects.all()
    else:
        proyectos = Proyecto.objects.filter(vendedor=user)
        clientes = Cliente.objects.filter(creado_por=user)
        cotizaciones = Cotizacion.objects.filter(creado_por=user)

    # Recent items
    proyectos_recientes = proyectos.order_by('-fecha_creacion')[:5]
    cotizaciones_recientes = cotizaciones.order_by('-fecha_creacion')[:5]

    # Summary stats
    stats = {
        'total_proyectos': proyectos.count(),
        'total_clientes': clientes.count(),
        'total_cotizaciones': cotizaciones.count(),
        'cotizaciones_pendientes': cotizaciones.filter(estado='borrador').count(),
        'cotizaciones_aprobadas': cotizaciones.filter(estado='aprobada').count(),
        'proyectos_activos': proyectos.exclude(
            estado__in=['completado', 'cancelado']
        ).count(),
        'valor_cotizaciones': cotizaciones.filter(
            estado__in=['enviada', 'aprobada']
        ).aggregate(total=Sum('total'))['total'] or 0,
    }

    # Equipment low stock alert
    equipos_bajo_stock = Equipo.objects.filter(activo=True, stock__lte=3, stock__gt=0)
    equipos_sin_stock = Equipo.objects.filter(activo=True, stock=0)

    context = {
        'stats': stats,
        'proyectos_recientes': proyectos_recientes,
        'cotizaciones_recientes': cotizaciones_recientes,
        'equipos_bajo_stock': equipos_bajo_stock,
        'equipos_sin_stock': equipos_sin_stock,
    }
    return render(request, 'core/dashboard.html', context)


# ──────────────────────────────────────────────
# CLIENTE VIEWS
# ──────────────────────────────────────────────

class ClienteListView(LoginRequiredMixin, ListView):
    model = Cliente
    template_name = 'core/clientes/cliente_list.html'
    context_object_name = 'clientes'
    paginate_by = 15

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_admin_role:
            qs = qs.filter(creado_por=self.request.user)
        search = self.request.GET.get('q')
        if search:
            qs = qs.filter(
                Q(nombre__icontains=search) |
                Q(email__icontains=search) |
                Q(ciudad__icontains=search)
            )
        return qs


class ClienteCreateView(LoginRequiredMixin, CreateView):
    model = Cliente
    form_class = ClienteForm
    template_name = 'core/clientes/cliente_form.html'
    success_url = reverse_lazy('cliente_list')

    def form_valid(self, form):
        form.instance.creado_por = self.request.user
        messages.success(self.request, 'Cliente creado exitosamente.')
        return super().form_valid(form)


class ClienteUpdateView(LoginRequiredMixin, UpdateView):
    model = Cliente
    form_class = ClienteForm
    template_name = 'core/clientes/cliente_form.html'
    success_url = reverse_lazy('cliente_list')

    def form_valid(self, form):
        messages.success(self.request, 'Cliente actualizado exitosamente.')
        return super().form_valid(form)


class ClienteDetailView(LoginRequiredMixin, DetailView):
    model = Cliente
    template_name = 'core/clientes/cliente_detail.html'
    context_object_name = 'cliente'


class ClienteDeleteView(LoginRequiredMixin, DeleteView):
    model = Cliente
    template_name = 'core/clientes/cliente_confirm_delete.html'
    success_url = reverse_lazy('cliente_list')

    def form_valid(self, form):
        messages.success(self.request, 'Cliente eliminado.')
        return super().form_valid(form)


# ──────────────────────────────────────────────
# PROYECTO VIEWS
# ──────────────────────────────────────────────

class ProyectoListView(LoginRequiredMixin, ListView):
    model = Proyecto
    template_name = 'core/proyectos/proyecto_list.html'
    context_object_name = 'proyectos'
    paginate_by = 15

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_admin_role:
            qs = qs.filter(vendedor=self.request.user)
        search = self.request.GET.get('q')
        if search:
            qs = qs.filter(
                Q(codigo__icontains=search) |
                Q(nombre__icontains=search) |
                Q(cliente__nombre__icontains=search)
            )
        tipo = self.request.GET.get('tipo')
        if tipo:
            qs = qs.filter(tipo_sistema=tipo)
        estado = self.request.GET.get('estado')
        if estado:
            qs = qs.filter(estado=estado)
        return qs


class ProyectoCreateView(LoginRequiredMixin, CreateView):
    model = Proyecto
    form_class = ProyectoForm
    template_name = 'core/proyectos/proyecto_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.vendedor = self.request.user
        messages.success(self.request, 'Proyecto creado exitosamente.')
        response = super().form_valid(form)
        return response

    def get_success_url(self):
        return reverse('proyecto_detail', kwargs={'pk': self.object.pk})


class ProyectoUpdateView(LoginRequiredMixin, UpdateView):
    model = Proyecto
    form_class = ProyectoForm
    template_name = 'core/proyectos/proyecto_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Proyecto actualizado.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('proyecto_detail', kwargs={'pk': self.object.pk})


class ProyectoDetailView(LoginRequiredMixin, DetailView):
    model = Proyecto
    template_name = 'core/proyectos/proyecto_detail.html'
    context_object_name = 'proyecto'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        proyecto = self.object
        context['cargas'] = proyecto.cargas.all()
        context['cotizaciones'] = proyecto.cotizaciones.all()
        
        # Calculate sizing from the latest quote's items (single source of truth)
        # If the project has quotes with equipment items, use those calculations
        # Otherwise, fall back to cached proyecto values
        cotizacion_mas_reciente = proyecto.cotizaciones.filter(
            items__isnull=False
        ).prefetch_related('items__equipo').order_by('-fecha_creacion').first()
        
        if cotizacion_mas_reciente:
            sizing_from_items = _calculate_sizing_from_items(cotizacion_mas_reciente, proyecto)
            context['sizing_from_quote'] = sizing_from_items
        
        return context


class ProyectoDeleteView(LoginRequiredMixin, DeleteView):
    model = Proyecto
    template_name = 'core/proyectos/proyecto_confirm_delete.html'
    success_url = reverse_lazy('proyecto_list')


@login_required
def proyecto_clonar(request, pk):
    """Clone (duplicate) an existing project with its related loads."""
    original = get_object_or_404(Proyecto, pk=pk)

    # Clone the project
    nuevo = Proyecto(
        nombre=f"{original.nombre} (Copia)",
        cliente=original.cliente,
        vendedor=request.user,
        tipo_sistema=original.tipo_sistema,
        estado=Proyecto.Estado.BORRADOR,
        latitud=original.latitud,
        longitud=original.longitud,
        direccion_instalacion=original.direccion_instalacion,
        consumo_mensual_factura_kwh=original.consumo_mensual_factura_kwh,
        hsp_promedio=original.hsp_promedio,
        radiacion_anual=original.radiacion_anual,
        potencia_pico_kwp=original.potencia_pico_kwp,
        numero_paneles=original.numero_paneles,
        generacion_mensual_kwh=original.generacion_mensual_kwh,
        porcentaje_cobertura=original.porcentaje_cobertura,
        autonomia_dias=original.autonomia_dias,
        capacidad_baterias_kwh=original.capacidad_baterias_kwh,
    )
    nuevo.save()  # auto-generates new codigo

    # Clone related loads (cargas)
    for carga in original.cargas.all():
        Carga.objects.create(
            proyecto=nuevo,
            tipo_carga=carga.tipo_carga,
            dispositivo=carga.dispositivo,
            cantidad=carga.cantidad,
            potencia_nominal_w=carga.potencia_nominal_w,
            horas_uso_dia=carga.horas_uso_dia,
            factor_potencia=carga.factor_potencia,
            carga_reactiva=carga.carga_reactiva,
            factor_arranque=carga.factor_arranque,
            prioridad=carga.prioridad,
        )

    messages.success(request, f'Proyecto clonado exitosamente como "{nuevo.codigo} - {nuevo.nombre}".')
    return redirect('proyecto_detail', pk=nuevo.pk)


# ──────────────────────────────────────────────
# CARGAS TIPO (LOAD CATALOG) CRUD
# ──────────────────────────────────────────────

class CargaTipoListView(LoginRequiredMixin, ListView):
    model = CargaTipo
    template_name = 'core/cargas/cargatipo_list.html'
    context_object_name = 'cargas_tipo'
    paginate_by = 20

    def get_queryset(self):
        qs = CargaTipo.objects.filter(activo=True)
        search = self.request.GET.get('q')
        if search:
            qs = qs.filter(
                Q(nombre__icontains=search) |
                Q(descripcion__icontains=search)
            )
        categoria = self.request.GET.get('categoria')
        if categoria:
            qs = qs.filter(categoria=categoria)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = CargaTipo.Categoria.choices
        context['total_cargas'] = CargaTipo.objects.filter(activo=True).count()
        return context


class CargaTipoCreateView(LoginRequiredMixin, CreateView):
    model = CargaTipo
    form_class = CargaTipoForm
    template_name = 'core/cargas/cargatipo_form.html'
    success_url = reverse_lazy('cargatipo_list')

    def form_valid(self, form):
        messages.success(self.request, 'Tipo de carga creado exitosamente.')
        return super().form_valid(form)


class CargaTipoUpdateView(LoginRequiredMixin, UpdateView):
    model = CargaTipo
    form_class = CargaTipoForm
    template_name = 'core/cargas/cargatipo_form.html'
    success_url = reverse_lazy('cargatipo_list')

    def form_valid(self, form):
        messages.success(self.request, 'Tipo de carga actualizado.')
        return super().form_valid(form)


class CargaTipoDetailView(LoginRequiredMixin, DetailView):
    model = CargaTipo
    template_name = 'core/cargas/cargatipo_detail.html'
    context_object_name = 'carga_tipo'


class CargaTipoDeleteView(LoginRequiredMixin, DeleteView):
    model = CargaTipo
    template_name = 'core/cargas/cargatipo_confirm_delete.html'
    success_url = reverse_lazy('cargatipo_list')

    def form_valid(self, form):
        messages.success(self.request, 'Tipo de carga eliminado.')
        return super().form_valid(form)


@login_required
def cargatipo_clonar(request, pk):
    """Clone (duplicate) an existing load type and open it in edit mode."""
    original = get_object_or_404(CargaTipo, pk=pk)

    nuevo = CargaTipo.objects.create(
        nombre=f"{original.nombre} (Copia)",
        categoria=original.categoria,
        potencia_nominal_w=original.potencia_nominal_w,
        horas_uso_dia=original.horas_uso_dia,
        factor_potencia=original.factor_potencia,
        carga_reactiva=original.carga_reactiva,
        factor_arranque=original.factor_arranque,
        descripcion=original.descripcion,
        activo=True,
    )

    return redirect('cargatipo_update', pk=nuevo.pk)


# ──────────────────────────────────────────────
# CARGAS (LOADS) MANAGEMENT
# ──────────────────────────────────────────────

@login_required
def proyecto_cargas(request, pk):
    """Manage electrical loads for a project using the load catalog."""
    proyecto = get_object_or_404(Proyecto, pk=pk)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'agregar_carga':
            tipo_carga_id = request.POST.get('tipo_carga')
            cantidad = int(request.POST.get('cantidad', 1))
            horas_uso = request.POST.get('horas_uso_dia')
            prioridad = request.POST.get('prioridad', 'importante')

            if tipo_carga_id:
                tipo_carga = get_object_or_404(CargaTipo, pk=tipo_carga_id)
                horas = float(horas_uso) if horas_uso else tipo_carga.horas_uso_dia
                Carga.objects.create(
                    proyecto=proyecto,
                    tipo_carga=tipo_carga,
                    dispositivo=tipo_carga.nombre,
                    cantidad=cantidad,
                    potencia_nominal_w=tipo_carga.potencia_nominal_w,
                    horas_uso_dia=horas,
                    factor_potencia=tipo_carga.factor_potencia,
                    carga_reactiva=tipo_carga.carga_reactiva,
                    factor_arranque=tipo_carga.factor_arranque,
                    prioridad=prioridad,
                )
                messages.success(request, f'Carga "{tipo_carga.nombre}" agregada al proyecto.')
            else:
                messages.warning(request, 'Selecciona un tipo de carga.')

        elif action == 'eliminar_carga':
            carga_id = request.POST.get('carga_id')
            carga = get_object_or_404(Carga, pk=carga_id, proyecto=proyecto)
            nombre = carga.dispositivo
            carga.delete()
            messages.success(request, f'Carga "{nombre}" eliminada.')

        elif action == 'actualizar_carga':
            carga_id = request.POST.get('carga_id')
            carga = get_object_or_404(Carga, pk=carga_id, proyecto=proyecto)
            carga.cantidad = int(request.POST.get('cantidad', carga.cantidad))
            carga.horas_uso_dia = float(request.POST.get('horas_uso_dia', carga.horas_uso_dia))
            carga.prioridad = request.POST.get('prioridad', carga.prioridad)
            carga.save()
            messages.success(request, f'Carga "{carga.dispositivo}" actualizada.')

        return redirect('proyecto_cargas', pk=proyecto.pk)

    # Load data
    cargas = proyecto.cargas.select_related('tipo_carga').all()
    tipos_carga = CargaTipo.objects.filter(activo=True)

    resumen = {
        'potencia_total': sum(c.potencia_total_w for c in cargas),
        'energia_diaria': sum(c.energia_diaria_wh for c in cargas),
        'potencia_arranque_max': max(
            (c.potencia_arranque_w for c in cargas), default=0
        ),
    }

    return render(request, 'core/proyectos/proyecto_cargas.html', {
        'proyecto': proyecto,
        'cargas': cargas,
        'tipos_carga': tipos_carga,
        'resumen': resumen,
        'prioridades': Carga.Prioridad.choices,
    })


# ──────────────────────────────────────────────
# DIMENSIONAMIENTO (SIZING)
# ──────────────────────────────────────────────

def _actualizar_dimensionamiento_y_resumen_proyecto(proyecto, cotizacion=None):
    """Recalculate sizing and executive financial fields stored in proyecto.

    This keeps project metrics in sync when quotes are created/updated so
    detail views and PDF reports always render current values.
    """
    cliente = proyecto.cliente

    if proyecto.tipo_sistema == 'on_grid':
        resultado = dimensionar_on_grid(
            consumo_mensual_kwh=proyecto.consumo_mensual_efectivo_kwh,
            tarifa_cop_kwh=cliente.tarifa_electrica,
            hsp=proyecto.hsp_promedio,
        )
        proyecto.potencia_pico_kwp = resultado.potencia_pico_kwp
        proyecto.numero_paneles = resultado.numero_paneles
        proyecto.generacion_mensual_kwh = resultado.generacion_mensual_kwh
        proyecto.porcentaje_cobertura = resultado.porcentaje_cobertura
        proyecto.ahorro_mensual = resultado.ahorro_mensual_cop
        proyecto.roi_anos = resultado.roi_anos
    elif proyecto.tipo_sistema in ('off_grid', 'hybrid'):
        cargas = proyecto.cargas.all()
        if cargas.exists():
            cargas_data = [{
                'potencia_w': c.potencia_nominal_w,
                'cantidad': c.cantidad,
                'horas_dia': c.horas_uso_dia,
                'factor_potencia': c.factor_potencia,
                'factor_arranque': c.factor_arranque,
                'carga_reactiva': c.carga_reactiva,
            } for c in cargas]

            resultado = dimensionar_off_grid(
                cargas=cargas_data,
                hsp=proyecto.hsp_promedio,
                autonomia_dias=proyecto.autonomia_dias,
            )

            proyecto.potencia_pico_kwp = resultado.potencia_pico_kwp
            proyecto.numero_paneles = resultado.numero_paneles
            proyecto.generacion_mensual_kwh = resultado.generacion_mensual_kwh
            proyecto.capacidad_baterias_kwh = resultado.capacidad_banco_kwh

            ahorro_mensual = min(
                resultado.generacion_mensual_kwh,
                proyecto.consumo_mensual_efectivo_kwh,
            ) * cliente.tarifa_electrica
            proyecto.ahorro_mensual = round(ahorro_mensual, 0)

    # Use quote total as latest investment baseline for executive summary / ROI.
    if cotizacion is not None:
        proyecto.costo_total = cotizacion.total

    ahorro_anual = float(proyecto.ahorro_mensual or 0) * 12
    costo_total = float(proyecto.costo_total or 0)
    if ahorro_anual > 0 and costo_total > 0:
        acumulado = 0
        incremento_tarifa = 5.0
        degradacion = 0.5
        for ano in range(1, 26):
            factor_tarifa = (1 + incremento_tarifa / 100) ** (ano - 1)
            factor_degradacion = (1 - degradacion / 100) ** (ano - 1)
            ahorro_ano = ahorro_anual * factor_tarifa * factor_degradacion
            acumulado += ahorro_ano
            if acumulado >= costo_total:
                ahorro_previo = acumulado - ahorro_ano
                fraccion = (costo_total - ahorro_previo) / ahorro_ano if ahorro_ano > 0 else 0
                proyecto.roi_anos = round(ano - 1 + fraccion, 1)
                break
        else:
            proyecto.roi_anos = 25

    if proyecto.estado == Proyecto.Estado.BORRADOR:
        proyecto.estado = Proyecto.Estado.EN_DISENO

    proyecto.save()


SUGERENCIA_KEY_TO_TIPO_EQUIPO = {
    'paneles': SelectedEquipo.TipoEquipo.PANEL,
    'inversores': SelectedEquipo.TipoEquipo.INVERSOR,
    'baterias': SelectedEquipo.TipoEquipo.BATERIA,
    'reguladores': SelectedEquipo.TipoEquipo.REGULADOR,
    'estructuras': SelectedEquipo.TipoEquipo.ESTRUCTURA,
}

TIPO_EQUIPO_TO_SUGERENCIA_KEY = {
    SelectedEquipo.TipoEquipo.PANEL: 'paneles',
    SelectedEquipo.TipoEquipo.INVERSOR: 'inversores',
    SelectedEquipo.TipoEquipo.BATERIA: 'baterias',
    SelectedEquipo.TipoEquipo.REGULADOR: 'reguladores',
    SelectedEquipo.TipoEquipo.ESTRUCTURA: 'estructuras',
}


def _sync_selected_from_suggestions(proyecto, sugerencias):
    """Persist default suggested equipment as selected when project has no manual selection."""
    if not sugerencias:
        return

    for key, sug in sugerencias.items():
        tipo_equipo = SUGERENCIA_KEY_TO_TIPO_EQUIPO.get(key, SelectedEquipo.TipoEquipo.OTRO)
        SelectedEquipo.objects.update_or_create(
            proyecto=proyecto,
            equipo=sug['equipo'],
            tipo_equipo=tipo_equipo,
            defaults={
                'cantidad': max(1, int(sug.get('cantidad', 1))),
                'activo': True,
            },
        )


def _build_suggestions_from_selected(equipos_seleccionados):
    """Build suggestion payload from selected equipment so both tabs show the same rows."""
    sugerencias = {}
    for sel in equipos_seleccionados:
        key = TIPO_EQUIPO_TO_SUGERENCIA_KEY.get(sel.tipo_equipo, f"{sel.tipo_equipo}s")
        sugerencias[key] = {
            'equipo': sel.equipo,
            'cantidad': sel.cantidad,
            'selected_id': sel.pk,
        }
    return sugerencias

@login_required
def proyecto_dimensionar(request, pk):
    """Run solar system sizing calculations."""
    proyecto = get_object_or_404(Proyecto, pk=pk)
    cliente = proyecto.cliente

    # Get PVGIS data
    pvgis_data = obtener_datos_pvgis(proyecto.latitud, proyecto.longitud)
    if pvgis_data.hsp_promedio > 0:
        proyecto.hsp_promedio = pvgis_data.hsp_promedio
        proyecto.radiacion_anual = pvgis_data.radiacion_anual

    resultado = None
    sugerencias = None
    proyeccion = None

    if proyecto.tipo_sistema == 'on_grid':
        resultado = dimensionar_on_grid(
            consumo_mensual_kwh=proyecto.consumo_mensual_efectivo_kwh,
            tarifa_cop_kwh=cliente.tarifa_electrica,
            hsp=proyecto.hsp_promedio,
        )
        # Update project
        proyecto.potencia_pico_kwp = resultado.potencia_pico_kwp
        proyecto.numero_paneles = resultado.numero_paneles
        proyecto.generacion_mensual_kwh = resultado.generacion_mensual_kwh
        proyecto.porcentaje_cobertura = resultado.porcentaje_cobertura
        proyecto.ahorro_mensual = resultado.ahorro_mensual_cop
        proyecto.costo_total = resultado.costo_estimado_sistema
        proyecto.roi_anos = resultado.roi_anos
        proyecto.estado = 'en_diseno'
        proyecto.save()

        # Financial projection
        proyeccion = calcular_proyeccion_financiera(
            ahorro_anual_cop=resultado.ahorro_anual_cop,
            costo_sistema=resultado.costo_estimado_sistema,
        )

    elif proyecto.tipo_sistema in ('off_grid', 'hybrid'):
        cargas = proyecto.cargas.all()
        if not cargas.exists():
            messages.warning(
                request,
                'Debes agregar las cargas eléctricas antes de dimensionar un sistema off-grid.'
            )
            return redirect('proyecto_cargas', pk=proyecto.pk)

        cargas_data = [{
            'potencia_w': c.potencia_nominal_w,
            'cantidad': c.cantidad,
            'horas_dia': c.horas_uso_dia,
            'factor_potencia': c.factor_potencia,
            'factor_arranque': c.factor_arranque,
            'carga_reactiva': c.carga_reactiva,
        } for c in cargas]

        resultado = dimensionar_off_grid(
            cargas=cargas_data,
            hsp=proyecto.hsp_promedio,
            autonomia_dias=proyecto.autonomia_dias,
        )

        proyecto.potencia_pico_kwp = resultado.potencia_pico_kwp
        proyecto.numero_paneles = resultado.numero_paneles
        proyecto.generacion_mensual_kwh = resultado.generacion_mensual_kwh
        proyecto.capacidad_baterias_kwh = resultado.capacidad_banco_kwh
        proyecto.costo_total = resultado.costo_estimado_sistema
        proyecto.estado = 'en_diseno'

        # Financial analysis for off-grid
        # Savings = what they would pay the grid for equivalent energy
        ahorro_mensual = min(
            resultado.generacion_mensual_kwh, proyecto.consumo_mensual_efectivo_kwh
        ) * cliente.tarifa_electrica
        ahorro_anual = ahorro_mensual * 12
        resultado.ahorro_mensual_cop = round(ahorro_mensual, 0)
        resultado.ahorro_anual_cop = round(ahorro_anual, 0)

        # ROI
        if ahorro_anual > 0:
            inversion = resultado.costo_estimado_sistema
            acumulado = 0
            incremento_tarifa = 5.0
            degradacion = 0.5
            for ano in range(1, 26):
                factor_tarifa = (1 + incremento_tarifa / 100) ** (ano - 1)
                factor_degradacion = (1 - degradacion / 100) ** (ano - 1)
                ahorro_ano = ahorro_anual * factor_tarifa * factor_degradacion
                acumulado += ahorro_ano
                if acumulado >= inversion and resultado.roi_anos == 0:
                    ahorro_previo = acumulado - ahorro_ano
                    fraccion = (inversion - ahorro_previo) / ahorro_ano if ahorro_ano > 0 else 0
                    resultado.roi_anos = round(ano - 1 + fraccion, 1)
            resultado.ahorro_acumulado_25_anos = round(acumulado, 0)
            if resultado.roi_anos == 0:
                resultado.roi_anos = 25

        proyecto.ahorro_mensual = resultado.ahorro_mensual_cop
        proyecto.roi_anos = resultado.roi_anos
        proyecto.save()

        # Financial projection
        if ahorro_anual > 0:
            proyeccion = calcular_proyeccion_financiera(
                ahorro_anual_cop=ahorro_anual,
                costo_sistema=resultado.costo_estimado_sistema,
            )

    # Suggest equipment
    if resultado:
        sugerencias = sugerir_equipos(proyecto, resultado)

    # Keep suggestions and selected equipment synchronized.
    equipos_seleccionados = proyecto.equipos_seleccionados.select_related('equipo').filter(activo=True)
    if resultado and not equipos_seleccionados.exists() and sugerencias:
        _sync_selected_from_suggestions(proyecto, sugerencias)
        equipos_seleccionados = proyecto.equipos_seleccionados.select_related('equipo').filter(activo=True)

    # If there is selected equipment, use it as the source of truth only when
    # the selected set can produce a valid sizing result.
    selected_has_panel = equipos_seleccionados.filter(
        tipo_equipo=SelectedEquipo.TipoEquipo.PANEL
    ).exists()
    selected_has_inversor = equipos_seleccionados.filter(
        tipo_equipo=SelectedEquipo.TipoEquipo.INVERSOR
    ).exists()

    selection_can_dimension = selected_has_panel and (
        proyecto.tipo_sistema not in (Proyecto.TipoSistema.ON_GRID, Proyecto.TipoSistema.HYBRID)
        or selected_has_inversor
    )

    # Use selected equipment as source of truth only when selection is complete enough.
    if equipos_seleccionados.exists() and selection_can_dimension:
        equipos_para_calcular = [
            {
                'tipo': sel.tipo_equipo,
                'equipo': sel.equipo,
                'cantidad': sel.cantidad,
                'notas': sel.notas,
            }
            for sel in equipos_seleccionados
        ]

        resultado = calculate_generation_with_equipment(
            selected_equipos=equipos_para_calcular,
            consumo_mensual_kwh=proyecto.consumo_mensual_efectivo_kwh,
            hsp=proyecto.hsp_promedio,
            tarifa_cop_kwh=cliente.tarifa_electrica,
            tipo_sistema=proyecto.tipo_sistema,
        )

        proyeccion = None
        if resultado.ahorro_anual_cop and resultado.costo_estimado_sistema:
            proyeccion = calcular_proyeccion_financiera(
                ahorro_anual_cop=resultado.ahorro_anual_cop,
                costo_sistema=resultado.costo_estimado_sistema,
            )

        sugerencias = _build_suggestions_from_selected(equipos_seleccionados)

        proyecto.potencia_pico_kwp = resultado.potencia_pico_kwp
        proyecto.numero_paneles = resultado.numero_paneles
        proyecto.generacion_mensual_kwh = resultado.generacion_mensual_kwh
        proyecto.porcentaje_cobertura = resultado.porcentaje_cobertura
        proyecto.ahorro_mensual = resultado.ahorro_mensual_cop
        proyecto.costo_total = resultado.costo_estimado_sistema
        proyecto.roi_anos = resultado.roi_anos
        if proyecto.estado == Proyecto.Estado.BORRADOR:
            proyecto.estado = Proyecto.Estado.EN_DISENO
        proyecto.save()

    # Get available equipment grouped by category
    equipos_por_categoria = {}
    for categoria_key, categoria_label in Equipo.Categoria.choices:
        equipos = Equipo.objects.filter(activo=True, categoria=categoria_key).order_by('fabricante', 'modelo')
        if equipos.exists():
            equipos_por_categoria[categoria_label] = equipos

    # Get selected equipment for this project
    equipos_seleccionados = proyecto.equipos_seleccionados.select_related('equipo').filter(activo=True)
    selected_equipo_ids = {sel.equipo_id for sel in equipos_seleccionados}

    context = {
        'proyecto': proyecto,
        'cliente': cliente,
        'resultado': resultado,
        'sugerencias': sugerencias,
        'pvgis_data': pvgis_data,
        'proyeccion': json.dumps(proyeccion) if proyeccion else None,
        'equipos_por_categoria': equipos_por_categoria,
        'equipos_seleccionados': equipos_seleccionados,
        'selected_equipo_ids': selected_equipo_ids,
    }
    return render(request, 'core/proyectos/proyecto_dimensionamiento.html', context)


# ──────────────────────────────────────────────
# PVGIS API ENDPOINT
# ──────────────────────────────────────────────

@login_required
def api_pvgis(request):
    """AJAX endpoint to fetch PVGIS data."""
    lat = request.GET.get('lat', 4.7110)
    lon = request.GET.get('lon', -74.0721)

    try:
        lat = float(lat)
        lon = float(lon)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Coordenadas inválidas'}, status=400)

    data = obtener_datos_pvgis(lat, lon)

    if data.error:
        return JsonResponse({'error': data.error}, status=500)

    return JsonResponse({
        'radiacion_mensual': data.radiacion_mensual,
        'radiacion_anual': data.radiacion_anual,
        'hsp_promedio': data.hsp_promedio,
        'hsp_minimo': data.hsp_minimo,
        'mes_minimo': data.mes_minimo,
    })


# ──────────────────────────────────────────────
# EQUIPO (INVENTORY) VIEWS
# ──────────────────────────────────────────────

class EquipoListView(LoginRequiredMixin, ListView):
    model = Equipo
    template_name = 'core/equipos/equipo_list.html'
    context_object_name = 'equipos'
    paginate_by = 20

    def get_queryset(self):
        qs = Equipo.objects.filter(activo=True)

        # Apply filters
        form = EquipoFilterForm(self.request.GET)
        if form.is_valid():
            if form.cleaned_data.get('categoria'):
                qs = qs.filter(categoria=form.cleaned_data['categoria'])
            if form.cleaned_data.get('fabricante'):
                qs = qs.filter(fabricante__icontains=form.cleaned_data['fabricante'])
            if form.cleaned_data.get('sistema'):
                qs = qs.filter(sistema_compatible=form.cleaned_data['sistema'])
            if form.cleaned_data.get('potencia_min'):
                qs = qs.filter(potencia_nominal_w__gte=form.cleaned_data['potencia_min'])
            if form.cleaned_data.get('potencia_max'):
                qs = qs.filter(potencia_nominal_w__lte=form.cleaned_data['potencia_max'])
            if form.cleaned_data.get('en_stock'):
                qs = qs.filter(stock__gt=0)
            if form.cleaned_data.get('buscar'):
                search = form.cleaned_data['buscar']
                qs = qs.filter(
                    Q(nombre__icontains=search) |
                    Q(modelo__icontains=search) |
                    Q(sku__icontains=search) |
                    Q(fabricante__icontains=search)
                )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = EquipoFilterForm(self.request.GET)
        context['total_equipos'] = Equipo.objects.filter(activo=True).count()
        return context


def calcular_hash_archivo(file_obj):
    """Calculate SHA256 hash of a file."""
    hasher = hashlib.sha256()
    for chunk in file_obj.chunks():
        hasher.update(chunk)
    return hasher.hexdigest()


class EquipoCreateView(LoginRequiredMixin, CreateView):
    model = Equipo
    form_class = EquipoForm
    template_name = 'core/equipos/equipo_form.html'
    success_url = reverse_lazy('equipo_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Handle multiple PDF uploads with deduplication
        archivos = self.request.FILES.getlist('archivos')
        for archivo in archivos:
            if archivo:
                # Calculate hash
                hash_archivo = calcular_hash_archivo(archivo)
                nombre_limpio = archivo.name.replace('.pdf', '').replace('_', ' ')
                
                # Check if file already exists
                archivo_obj, created = Archivo.objects.get_or_create(
                    hash_archivo=hash_archivo,
                    defaults={
                        'archivo': archivo,
                        'nombre': nombre_limpio,
                    }
                )
                
                # Add to equipment if not already added
                if not self.object.archivos.filter(pk=archivo_obj.pk).exists():
                    self.object.archivos.add(archivo_obj)
        
        messages.success(self.request, 'Equipo agregado al inventario.')
        return response


class EquipoUpdateView(LoginRequiredMixin, UpdateView):
    model = Equipo
    form_class = EquipoForm
    template_name = 'core/equipos/equipo_form.html'
    success_url = reverse_lazy('equipo_list')

    def form_valid(self, form):
        form.instance.fecha_actualizacion_precio = timezone.now().date()
        response = super().form_valid(form)
        
        # Handle multiple PDF uploads with deduplication
        archivos = self.request.FILES.getlist('archivos')
        for archivo in archivos:
            if archivo:
                # Calculate hash
                hash_archivo = calcular_hash_archivo(archivo)
                nombre_limpio = archivo.name.replace('.pdf', '').replace('_', ' ')
                
                # Check if file already exists
                archivo_obj, created = Archivo.objects.get_or_create(
                    hash_archivo=hash_archivo,
                    defaults={
                        'archivo': archivo,
                        'nombre': nombre_limpio,
                    }
                )
                
                # Add to equipment if not already added
                if not self.object.archivos.filter(pk=archivo_obj.pk).exists():
                    self.object.archivos.add(archivo_obj)
        
        messages.success(self.request, 'Equipo actualizado.')
        return response
        return response


class EquipoDetailView(LoginRequiredMixin, DetailView):
    model = Equipo
    template_name = 'core/equipos/equipo_detail.html'
    context_object_name = 'equipo'


class EquipoDeleteView(AdminRequiredMixin, DeleteView):
    model = Equipo
    template_name = 'core/equipos/equipo_confirm_delete.html'
    success_url = reverse_lazy('equipo_list')

    def form_valid(self, form):
        messages.success(self.request, 'Equipo eliminado del inventario.')
        return super().form_valid(form)


@login_required
def equipo_clonar(request, pk):
    """Clone (duplicate) an existing equipment item."""
    original = get_object_or_404(Equipo, pk=pk)

    nuevo = Equipo(
        nombre=f"{original.nombre} (Copia)",
        modelo=f"{original.modelo} (Copia)",
        fabricante=original.fabricante,
        categoria=original.categoria,
        sku=f"{original.sku}-COPY-{timezone.now().strftime('%y%m%d%H%M%S')}",
        descripcion=original.descripcion,
        potencia_nominal_w=original.potencia_nominal_w,
        voltaje_nominal=original.voltaje_nominal,
        corriente_nominal=original.corriente_nominal,
        eficiencia=original.eficiencia,
        datos_tecnicos=original.datos_tecnicos,
        sistema_compatible=original.sistema_compatible,
        garantia_anos=original.garantia_anos,
        largo_mm=original.largo_mm,
        ancho_mm=original.ancho_mm,
        alto_mm=original.alto_mm,
        peso_kg=original.peso_kg,
        precio_proveedor=original.precio_proveedor,
        precio_venta=original.precio_venta,
        margen_porcentaje=original.margen_porcentaje,
        stock=0,
        activo=True,
    )
    nuevo.save()

    messages.success(request, f'Equipo clonado exitosamente como "{nuevo.fabricante} {nuevo.modelo}".')
    return redirect('equipo_update', pk=nuevo.pk)


# ──────────────────────────────────────────────
# COTIZACIÓN VIEWS
# ──────────────────────────────────────────────

class CotizacionListView(LoginRequiredMixin, ListView):
    model = Cotizacion
    template_name = 'core/cotizaciones/cotizacion_list.html'
    context_object_name = 'cotizaciones'
    paginate_by = 15

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_admin_role:
            qs = qs.filter(creado_por=self.request.user)
        search = self.request.GET.get('q')
        if search:
            qs = qs.filter(
                Q(numero__icontains=search) |
                Q(proyecto__nombre__icontains=search) |
                Q(proyecto__cliente__nombre__icontains=search)
            )
        estado = self.request.GET.get('estado')
        if estado:
            qs = qs.filter(estado=estado)
        return qs


class CotizacionCreateView(LoginRequiredMixin, CreateView):
    model = Cotizacion
    form_class = CotizacionForm
    template_name = 'core/cotizaciones/cotizacion_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['items_formset'] = CotizacionItemFormSet(self.request.POST)
        else:
            context['items_formset'] = CotizacionItemFormSet()

            # Pre-fill from sizing suggestions if project is given
            proyecto_id = self.request.GET.get('proyecto')
            if proyecto_id:
                try:
                    context['form'].initial['proyecto'] = int(proyecto_id)
                except (ValueError, TypeError):
                    pass
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        items_formset = context['items_formset']

        form.instance.creado_por = self.request.user

        if items_formset.is_valid():
            self.object = form.save()
            items_formset.instance = self.object
            items_formset.save()
            self.object.calcular_totales()
            _actualizar_dimensionamiento_y_resumen_proyecto(
                self.object.proyecto,
                cotizacion=self.object,
            )
            messages.success(self.request, 'Cotización creada exitosamente.')
            return redirect('cotizacion_detail', pk=self.object.pk)
        else:
            # In manual total mode, ignore formset errors for empty price fields
            if form.cleaned_data.get('usar_total_manual'):
                self.object = form.save()
                items_formset.instance = self.object
                # Save only forms that have an equipo selected
                for item_form in items_formset:
                    if item_form.cleaned_data and item_form.cleaned_data.get('equipo') and not item_form.cleaned_data.get('DELETE'):
                        item = item_form.save(commit=False)
                        item.cotizacion = self.object
                        if not item.precio_unitario:
                            item.precio_unitario = 0
                        item.save()
                self.object.calcular_totales()
                _actualizar_dimensionamiento_y_resumen_proyecto(
                    self.object.proyecto,
                    cotizacion=self.object,
                )
                messages.success(self.request, 'Cotización creada exitosamente.')
                return redirect('cotizacion_detail', pk=self.object.pk)
            return self.render_to_response(context)


class CotizacionDetailView(LoginRequiredMixin, DetailView):
    model = Cotizacion
    template_name = 'core/cotizaciones/cotizacion_detail.html'
    context_object_name = 'cotizacion'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cotizacion = self.object
        proyecto = cotizacion.proyecto
        cliente = proyecto.cliente
        context['items'] = cotizacion.items.select_related('equipo').all()
        context['proyecto'] = proyecto
        context['cliente'] = cliente

        # Get electrical loads for off-grid projects
        cargas = proyecto.cargas.all() if proyecto.tipo_sistema != Proyecto.TipoSistema.ON_GRID else []
        context['cargas'] = cargas

        # Calculate sizing results from items (overrides proyecto values)
        sizing_from_items = _calculate_sizing_from_items(cotizacion, proyecto)
        context['sizing'] = sizing_from_items

        panel_items = [
            item for item in context['items']
            if item.equipo.categoria == Equipo.Categoria.PANEL
            and item.equipo.largo_mm
            and item.equipo.ancho_mm
        ]
        if panel_items:
            panel_ref = panel_items[0]
            largo_mm = float(panel_ref.equipo.largo_mm)
            ancho_mm = float(panel_ref.equipo.ancho_mm)
            area_panel_m2 = (largo_mm * ancho_mm) / 1_000_000
            numero_paneles = sum(int(item.cantidad or 0) for item in panel_items)
            area_total_m2 = area_panel_m2 * numero_paneles * 1.10
            context['panel_area'] = {
                'largo_mm': largo_mm,
                'ancho_mm': ancho_mm,
                'area_panel_m2': round(area_panel_m2, 3),
                'numero_paneles': numero_paneles,
                'factor_extra': 10,
                'area_total_m2': round(area_total_m2, 2),
                'panel_nombre': panel_ref.equipo.nombre,
            }

        # Financial projection for ROI chart
        ahorro_anual = float(proyecto.ahorro_mensual or 0) * 12
        costo = float(proyecto.costo_total or 0)
        if ahorro_anual > 0 and costo > 0:
            proyeccion = calcular_proyeccion_financiera(
                ahorro_anual_cop=ahorro_anual,
                costo_sistema=costo,
            )
            context['proyeccion'] = json.dumps(proyeccion)
        return context


class CotizacionUpdateView(LoginRequiredMixin, UpdateView):
    model = Cotizacion
    form_class = CotizacionForm
    template_name = 'core/cotizaciones/cotizacion_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['items_formset'] = CotizacionItemFormSet(
                self.request.POST, instance=self.object
            )
        else:
            context['items_formset'] = CotizacionItemFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        items_formset = context['items_formset']

        if items_formset.is_valid():
            self.object = form.save()
            items_formset.save()
            self.object.calcular_totales()
            _actualizar_dimensionamiento_y_resumen_proyecto(
                self.object.proyecto,
                cotizacion=self.object,
            )
            messages.success(self.request, 'Cotización actualizada.')
            return redirect('cotizacion_detail', pk=self.object.pk)
        else:
            # In manual total mode, ignore formset errors for empty price fields
            if form.cleaned_data.get('usar_total_manual'):
                self.object = form.save()
                # Delete items marked for deletion
                for item_form in items_formset:
                    if item_form.cleaned_data and item_form.cleaned_data.get('DELETE') and item_form.instance.pk:
                        item_form.instance.delete()
                # Save items that have an equipo selected
                for item_form in items_formset:
                    if item_form.cleaned_data and item_form.cleaned_data.get('equipo') and not item_form.cleaned_data.get('DELETE'):
                        item = item_form.save(commit=False)
                        item.cotizacion = self.object
                        if not item.precio_unitario:
                            item.precio_unitario = 0
                        item.save()
                self.object.calcular_totales()
                _actualizar_dimensionamiento_y_resumen_proyecto(
                    self.object.proyecto,
                    cotizacion=self.object,
                )
                messages.success(self.request, 'Cotización actualizada.')
                return redirect('cotizacion_detail', pk=self.object.pk)
            return self.render_to_response(context)


class CotizacionDeleteView(LoginRequiredMixin, DeleteView):
    model = Cotizacion
    template_name = 'core/cotizaciones/cotizacion_confirm_delete.html'
    success_url = reverse_lazy('cotizacion_list')


@login_required
def cotizacion_clonar(request, pk):
    """Clone (duplicate) an existing quote with its items."""
    original = get_object_or_404(Cotizacion, pk=pk)

    nueva = Cotizacion(
        proyecto=original.proyecto,
        estado=Cotizacion.Estado.BORRADOR,
        tipo_cliente=original.tipo_cliente,
        descuento_porcentaje=original.descuento_porcentaje,
        iva_porcentaje=original.iva_porcentaje,
        usar_total_manual=original.usar_total_manual,
        total_manual=original.total_manual,
        costo_instalacion=original.costo_instalacion,
        costo_transporte=original.costo_transporte,
        fecha_emision=timezone.now().date(),
        dias_validez=original.dias_validez,
        condiciones=original.condiciones,
        creado_por=request.user,
    )
    nueva.save()  # auto-generates new numero

    # Clone items
    for item in original.items.all():
        CotizacionItem.objects.create(
            cotizacion=nueva,
            equipo=item.equipo,
            cantidad=item.cantidad,
            precio_unitario=item.precio_unitario,
            descuento_item=item.descuento_item,
            aplica_iva=item.aplica_iva,
        )

    nueva.calcular_totales()

    messages.success(request, f'Cotización clonada exitosamente como "{nueva.numero}".')
    return redirect('cotizacion_detail', pk=nueva.pk)


@login_required
def cotizacion_crear_desde_proyecto(request, pk):
    """Create a quote pre-filled with sizing results or selected equipment."""
    proyecto = get_object_or_404(Proyecto, pk=pk)

    if not proyecto.potencia_pico_kwp:
        messages.warning(request, 'Primero debes dimensionar el proyecto.')
        return redirect('proyecto_dimensionar', pk=pk)

    # Create quote
    cotizacion = Cotizacion(
        proyecto=proyecto,
        creado_por=request.user,
    )
    cotizacion.save()

    # Check if equipment_ids were provided (POST from equipment selection form)
    equipment_ids = request.POST.getlist('equipment_ids') if request.method == 'POST' else []
    
    if equipment_ids:
        # Use selected equipment instead of suggestions
        # Note: equipment_ids are SelectedEquipo.pk, not Equipo.pk
        selected_equipos = SelectedEquipo.objects.filter(
            proyecto=proyecto,
            id__in=equipment_ids
        ).select_related('equipo')
        
        for sel in selected_equipos:
            CotizacionItem.objects.create(
                cotizacion=cotizacion,
                equipo=sel.equipo,
                cantidad=sel.cantidad,
                precio_unitario=sel.equipo.precio_venta,
            )
        
        items_message = f'{selected_equipos.count()} equipo(s) seleccionado(s)'
    else:
        # Fall back to automatic suggestions (existing behavior)
        if proyecto.tipo_sistema == 'on_grid':
            resultado = dimensionar_on_grid(
                consumo_mensual_kwh=proyecto.cliente.consumo_mensual_kwh,
                tarifa_cop_kwh=proyecto.cliente.tarifa_electrica,
                hsp=proyecto.hsp_promedio,
            )
        else:
            cargas = proyecto.cargas.all()
            cargas_data = [{
                'potencia_w': c.potencia_nominal_w,
                'cantidad': c.cantidad,
                'horas_dia': c.horas_uso_dia,
                'factor_potencia': c.factor_potencia,
                'factor_arranque': c.factor_arranque,
                'carga_reactiva': c.carga_reactiva,
            } for c in cargas]
            resultado = dimensionar_off_grid(
                cargas=cargas_data,
                hsp=proyecto.hsp_promedio,
                autonomia_dias=proyecto.autonomia_dias,
            )

        sugerencias = sugerir_equipos(proyecto, resultado)

        for key, sug in sugerencias.items():
            equipo = sug['equipo']
            CotizacionItem.objects.create(
                cotizacion=cotizacion,
                equipo=equipo,
                cantidad=sug['cantidad'],
                precio_unitario=equipo.precio_venta,
            )
        
        items_message = 'equipos sugeridos'

    cotizacion.calcular_totales()
    _actualizar_dimensionamiento_y_resumen_proyecto(
        cotizacion.proyecto,
        cotizacion=cotizacion,
    )
    proyecto.estado = 'cotizado'
    proyecto.save()

    messages.success(request, f'Cotización {cotizacion.numero} creada con {items_message}.')
    return redirect('cotizacion_detail', pk=cotizacion.pk)


# ──────────────────────────────────────────────
# REPORT VIEWS
# ──────────────────────────────────────────────

@login_required
def cotizacion_pdf(request, pk):
    """Generate PDF report for a quote."""
    from core.calculations.reports import generar_pdf_cotizacion

    cotizacion = get_object_or_404(Cotizacion, pk=pk)
    _actualizar_dimensionamiento_y_resumen_proyecto(
        cotizacion.proyecto,
        cotizacion=cotizacion,
    )
    pdf_buffer = generar_pdf_cotizacion(cotizacion)

    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="cotizacion_{cotizacion.numero}.pdf"'
    return response


@login_required
def cotizacion_excel(request, pk):
    """Generate Excel report for a quote."""
    from core.calculations.reports import generar_excel_cotizacion

    cotizacion = get_object_or_404(Cotizacion, pk=pk)
    excel_buffer = generar_excel_cotizacion(cotizacion)

    response = HttpResponse(
        excel_buffer,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="cotizacion_{cotizacion.numero}.xlsx"'
    return response


# SVG Chart Generation Functions for Weasyprint PDF
def _generate_consumo_comparison_svg(actual, generacion, cobertura):
    """Generate SVG bar chart for consumption vs solar generation."""
    width, height = 500, 280
    margin = 50
    chart_width = width - 2 * margin
    chart_height = height - 2 * margin
    
    max_value = max(actual, generacion) * 1.1
    bar_width = chart_width / 3 / 2.5
    bar_spacing = chart_width / 3
    
    actual_height = (actual / max_value) * chart_height if max_value > 0 else 0
    generacion_height = (generacion / max_value) * chart_height if max_value > 0 else 0
    
    x1 = margin + bar_spacing * 0.5
    x2 = margin + bar_spacing * 1.5
    
    svg = f'''<svg width="100%" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
        <line x1="{margin}" y1="{margin + chart_height}" x2="{margin + chart_width}" y2="{margin + chart_height}" stroke="#e5e7eb" stroke-width="1"/>
        <rect x="{x1 - bar_width/2}" y="{margin + chart_height - actual_height}" width="{bar_width}" height="{actual_height}" fill="#ef4444"/>
        <text x="{x1}" y="{margin + chart_height + 25}" text-anchor="middle" font-size="11" font-family="Arial">Consumo</text>
        <text x="{x1}" y="{margin + chart_height - actual_height - 5}" text-anchor="middle" font-size="10" font-family="Arial" font-weight="bold">{actual:.0f}</text>
        <rect x="{x2 - bar_width/2}" y="{margin + chart_height - generacion_height}" width="{bar_width}" height="{generacion_height}" fill="#22c55e"/>
        <text x="{x2}" y="{margin + chart_height + 25}" text-anchor="middle" font-size="11" font-family="Arial">Generación</text>
        <text x="{x2}" y="{margin + chart_height - generacion_height - 5}" text-anchor="middle" font-size="10" font-family="Arial" font-weight="bold">{generacion:.0f}</text>
        <text x="15" y="{margin}" font-size="10" font-family="Arial" fill="#666">kWh</text>
    </svg>'''
    return svg


def _generate_radiacion_svg(radiacion_mensual):
    """Generate SVG bar chart for monthly solar radiation - min is red, rest is amber."""
    width, height = 500, 250
    margin = 50
    chart_width = width - 2 * margin
    chart_height = height - 2 * margin
    
    months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    if not radiacion_mensual:
        return None
    
    max_value = max(radiacion_mensual) * 1.1
    min_value = min(radiacion_mensual)
    
    bar_width = chart_width / len(radiacion_mensual) * 0.7
    bar_spacing = chart_width / len(radiacion_mensual)
    
    bars = ''
    labels = ''
    for i, value in enumerate(radiacion_mensual):
        x = margin + i * bar_spacing + bar_spacing/2
        height_scaled = (value / max_value) * chart_height if max_value > 0 else 0
        y = margin + chart_height - height_scaled
        
        # Minimum radiation is red, rest is amber (like web)
        color = '#ef4444' if value == min_value else '#f59e0b'
        bars += f'<rect x="{x - bar_width/2}" y="{y}" width="{bar_width}" height="{height_scaled}" fill="{color}"/>\n'
        bars += f'<text x="{x}" y="{y - 3}" text-anchor="middle" font-size="8" font-family="Arial" font-weight="bold">{value:.1f}</text>\n'
        labels += f'<text x="{x}" y="{margin + chart_height + 16}" text-anchor="middle" font-size="9" font-family="Arial">{months[i]}</text>\n'
    
    svg = f'''<svg width="100%" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
        <line x1="{margin}" y1="{margin + chart_height}" x2="{margin + chart_width}" y2="{margin + chart_height}" stroke="#e5e7eb" stroke-width="1"/>
        {bars}
        {labels}
        <text x="5" y="{margin}" font-size="9" font-family="Arial" fill="#666">kWh/m²</text>
    </svg>'''
    return svg


def _generate_hsp_svg(hsp_mensual, hsp_promedio=None):
    """Generate SVG bar chart for HSP - min red, max green, rest blue, with average line."""
    width, height = 500, 250
    margin = 50
    chart_width = width - 2 * margin
    chart_height = height - 2 * margin
    
    months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    if not hsp_mensual:
        return None
    
    max_value = max(hsp_mensual) * 1.1
    min_hsp = min(hsp_mensual)
    max_hsp = max(hsp_mensual)
    if hsp_promedio is None:
        hsp_promedio = sum(hsp_mensual) / len(hsp_mensual)
    
    bar_width = chart_width / len(hsp_mensual) * 0.7
    bar_spacing = chart_width / len(hsp_mensual)
    
    bars = ''
    labels = ''
    for i, value in enumerate(hsp_mensual):
        x = margin + i * bar_spacing + bar_spacing/2
        height_scaled = (value / max_value) * chart_height if max_value > 0 else 0
        y = margin + chart_height - height_scaled
        
        # Color: min red, max green, rest blue (like web)
        if value == min_hsp:
            color = '#ef4444'
        elif value == max_hsp:
            color = '#22c55e'
        else:
            color = '#3b82f6'
        
        bars += f'<rect x="{x - bar_width/2}" y="{y}" width="{bar_width}" height="{height_scaled}" fill="{color}"/>\n'
        bars += f'<text x="{x}" y="{y - 3}" text-anchor="middle" font-size="8" font-family="Arial" font-weight="bold">{value:.2f}</text>\n'
        labels += f'<text x="{x}" y="{margin + chart_height + 16}" text-anchor="middle" font-size="9" font-family="Arial">{months[i]}</text>\n'
    
    # Average line (amber/orange, dashed, like web)
    avg_line_y = margin + chart_height - (hsp_promedio / max_value) * chart_height if max_value > 0 else margin + chart_height
    
    svg = f'''<svg width="100%" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
        <line x1="{margin}" y1="{margin + chart_height}" x2="{margin + chart_width}" y2="{margin + chart_height}" stroke="#e5e7eb" stroke-width="1"/>
        <line x1="{margin}" y1="{avg_line_y}" x2="{margin + chart_width}" y2="{avg_line_y}" stroke="#f59e0b" stroke-width="2" stroke-dasharray="4,3"/>
        {bars}
        {labels}
        <text x="5" y="{margin}" font-size="9" font-family="Arial" fill="#666">h/día</text>
        <text x="5" y="{avg_line_y + 12}" font-size="8" font-family="Arial" fill="#f59e0b" font-weight="bold">Prom: {hsp_promedio:.2f}</text>
    </svg>'''
    return svg


def _generate_proyeccion_financiera_svg(anos, ahorro_acumulado, costo_total):
    """Generate SVG line chart for financial projection with green area fill."""
    if not anos or not ahorro_acumulado:
        return None
    
    width, height = 500, 280
    margin = 60
    chart_width = width - 2 * margin
    chart_height = height - 2 * margin
    
    # Calculate scaling
    max_ahorro = max(ahorro_acumulado) if ahorro_acumulado else 1
    min_ahorro = min(ahorro_acumulado) if ahorro_acumulado else 0
    total_range = max_ahorro - min_ahorro if max_ahorro != min_ahorro else 1
    
    # Build path data for the line
    points = []
    for i, (year, ahorro) in enumerate(zip(anos, ahorro_acumulado)):
        x = margin + (year / 25) * chart_width
        y_value = (ahorro - min_ahorro) / total_range
        y = margin + chart_height - (y_value * chart_height)
        points.append(f"{x},{y}")
    
    line_path = " L ".join(points)
    
    # Area path (for filling)
    area_path = f"M {margin},{margin + chart_height} L {line_path} L {margin + chart_width},{margin + chart_height} Z"
    
    # Equilibrium line (red, dashed, at y=0)
    eq_y = margin + chart_height
    
    # Find breakeven point (where ahorro crosses zero)
    breakeven_year = None
    for year, ahorro in zip(anos, ahorro_acumulado):
        if ahorro >= 0:
            breakeven_year = year
            break
    
    svg = f'''<svg width="100%" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="areaGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" style="stop-color:#22c55e;stop-opacity:0.3" />
                <stop offset="100%" style="stop-color:#22c55e;stop-opacity:0.05" />
            </linearGradient>
        </defs>
        
        <!-- Grid -->
        <line x1="{margin}" y1="{margin + chart_height}" x2="{margin + chart_width}" y2="{margin + chart_height}" stroke="#e5e7eb" stroke-width="1"/>
        
        <!-- Area under curve -->
        <path d="{area_path}" fill="url(#areaGradient)"/>
        
        <!-- Line -->
        <polyline points="{line_path}" fill="none" stroke="#22c55e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        
        <!-- Equilibrium line (red dashed) -->
        <line x1="{margin}" y1="{eq_y}" x2="{margin + chart_width}" y2="{eq_y}" stroke="#ef4444" stroke-width="2" stroke-dasharray="4,3"/>
        
        <!-- Axes -->
        <line x1="{margin}" y1="{margin}" x2="{margin}" y2="{margin + chart_height}" stroke="#1f2937" stroke-width="1"/>
        <line x1="{margin}" y1="{margin + chart_height}" x2="{margin + chart_width}" y2="{margin + chart_height}" stroke="#1f2937" stroke-width="1"/>
        
        <!-- Axis labels -->
        <text x="{margin + chart_width/2}" y="{height - 5}" text-anchor="middle" font-size="10" font-family="Arial" fill="#666">Años</text>
        <text x="10" y="{margin + chart_height/2}" text-anchor="middle" font-size="9" font-family="Arial" fill="#666" transform="rotate(-90 10 {margin + chart_height/2})">COP</text>
        
        <!-- Year markers -->
        <text x="{margin}" y="{margin + chart_height + 18}" text-anchor="middle" font-size="9" font-family="Arial" fill="#666">0</text>
        <text x="{margin + chart_width}" y="{margin + chart_height + 18}" text-anchor="middle" font-size="9" font-family="Arial" fill="#666">25</text>
        
        <!-- Breakeven indicator if applicable -->
        {'<text x="' + str(margin + chart_width/2) + '" y="' + str(margin - 10) + '" text-anchor="middle" font-size="9" font-family="Arial" font-weight="bold" fill="#22c55e">Equilibrio: ' + str(int(breakeven_year or 0)) + ' años</text>' if breakeven_year else ''}
    </svg>'''
    return svg


def _generate_panel_solar_svg(largo_mm, ancho_mm, numero_paneles, area_total):
    """Generate SVG diagram of a solar panel with dimensions."""
    width, height = 300, 180
    panel_width = 180
    panel_height = 120
    
    # Panel position (centered in viewBox)
    px = 30
    py = 20
    
    # Width line position (right side)
    width_line_x = px + panel_width + 15
    
    # Grid lines for solar cells (6 cols x 3 rows)
    grid = ''
    for i in range(7):  # 6 columns = 7 lines
        x = px + i * (panel_width / 6)
        grid += f'<line x1="{x}" y1="{py}" x2="{x}" y2="{py + panel_height}" stroke="#334155" stroke-width="1"/>\n'
    for i in range(4):  # 3 rows = 4 lines
        y = py + i * (panel_height / 3)
        grid += f'<line x1="{px}" y1="{y}" x2="{px + panel_width}" y2="{y}" stroke="#334155" stroke-width="1"/>\n'
    
    svg = f'''<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="width: 100%; max-width: 400px; height: auto;">
        <!-- Panel background -->
        <rect x="{px}" y="{py}" width="{panel_width}" height="{panel_height}" rx="6" fill="#0f172a" stroke="#1e293b" stroke-width="3"/>
        
        <!-- Solar cells grid -->
        <g stroke="#334155" stroke-width="1">
            {grid}
        </g>
        
        <!-- Length dimension line (bottom, teal) -->
        <line x1="{px}" y1="156" x2="{px + panel_width}" y2="156" stroke="#0f766e" stroke-width="2"/>
        
        <!-- Length dimension arrows (teal) -->
        <polygon points="{px},156 {px + 8},152 {px + 8},160" fill="#0f766e"/>
        <polygon points="{px + panel_width},156 {px + panel_width - 8},152 {px + panel_width - 8},160" fill="#0f766e"/>
        
        <!-- Length label -->
        <text x="{px + panel_width/2}" y="172" text-anchor="middle" font-size="11" font-family="Arial" fill="#0f766e" font-weight="500">
            Largo: {largo_mm:.0f} mm
        </text>
        
        <!-- Width dimension line (right, amber) -->
        <line x1="{width_line_x}" y1="{py}" x2="{width_line_x}" y2="{py + panel_height}" stroke="#f59e0b" stroke-width="2"/>
        
        <!-- Width dimension arrows (amber) -->
        <polygon points="{width_line_x},{py} {width_line_x - 4},{py + 8} {width_line_x + 4},{py + 8}" fill="#f59e0b"/>
        <polygon points="{width_line_x},{py + panel_height} {width_line_x - 4},{py + panel_height - 8} {width_line_x + 4},{py + panel_height - 8}" fill="#f59e0b"/>
        
        <!-- Width label (rotated) -->
        <text x="{width_line_x + 13}" y="{py + panel_height/2}" text-anchor="middle" font-size="11" font-family="Arial" fill="#f59e0b" font-weight="500" 
              transform="rotate(90 {width_line_x + 13} {py + panel_height/2})">
            Ancho: {ancho_mm:.0f} mm
        </text>
    </svg>'''
    return svg


def _generate_cost_distribution_svg(labels, values):
    """Generate SVG legend for cost distribution."""
    if not labels or not values:
        return None
    
    total = sum(values)
    percentages = [v / total * 100 for v in values] if total > 0 else []
    
    width, height = 100 + len(labels) * 80
    height = max(200, len(labels) * 22 + 40)
    
    colors = ['#f59e0b', '#10b981', '#3b82f6', '#8b5cf6', '#ef4444', '#06b6d4', '#ec4899', '#84cc16']
    
    legend_items = ''
    for i, (label, pct) in enumerate(zip(labels, percentages)):
        y = 30 + i * 22
        color = colors[i % len(colors)]
        legend_items += f'<rect x="20" y="{y - 10}" width="14" height="14" fill="{color}"/>\n'
        legend_items += f'<text x="40" y="{y}" font-size="10" font-family="Arial" fill="#1f2937"><tspan font-weight="bold">{label}:</tspan> {pct:.1f}%</text>\n'
    
    svg = f'''<svg width="100%" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
        <text x="20" y="20" text-anchor="start" font-size="12" font-family="Arial" fill="#1f2937" font-weight="bold">Distribución de Costos</text>
        {legend_items}
    </svg>'''
    return svg


@login_required
def cotizacion_pdf_weasyprint(request, pk):
    """Generate PDF report for a quote using Weasyprint (HTML+CSS alternative)."""
    try:
        cotizacion = get_object_or_404(Cotizacion, pk=pk)
        _actualizar_dimensionamiento_y_resumen_proyecto(
            cotizacion.proyecto,
            cotizacion=cotizacion,
        )

        proyecto = cotizacion.proyecto
        cliente = proyecto.cliente
        items = cotizacion.items.select_related('equipo').all()
        cargas = proyecto.cargas.all() if proyecto.tipo_sistema != Proyecto.TipoSistema.ON_GRID else []
        
        # Calculate sizing results
        sizing_from_items = _calculate_sizing_from_items(cotizacion, proyecto)
        
        # Calculate panel area
        panel_area = None
        panel_items = [
            item for item in items
            if item.equipo.categoria == Equipo.Categoria.PANEL
            and item.equipo.largo_mm
            and item.equipo.ancho_mm
        ]
        if panel_items:
            panel_ref = panel_items[0]
            largo_mm = float(panel_ref.equipo.largo_mm)
            ancho_mm = float(panel_ref.equipo.ancho_mm)
            area_panel_m2 = (largo_mm * ancho_mm) / 1_000_000
            numero_paneles = sum(int(item.cantidad or 0) for item in panel_items)
            area_total_m2 = area_panel_m2 * numero_paneles * 1.10
            panel_area = {
                'largo_mm': largo_mm,
                'ancho_mm': ancho_mm,
                'area_panel_m2': round(area_panel_m2, 3),
                'numero_paneles': numero_paneles,
                'factor_extra': 10,
                'area_total_m2': round(area_total_m2, 2),
                'panel_nombre': panel_ref.equipo.nombre,
            }

        # Get company settings
        company = CompanySettings.load()
        
        # Convert company logo to absolute URL for Weasyprint
        if company.logo:
            company.logo = request.build_absolute_uri(company.logo.url)
        
        # Build chart payload (only data, no image generation)
        chart_payload = build_cotizacion_charts_payload(cotizacion)
        
        # Prepare chart data for template display
        chart_data = {}
        consumo_svg = None
        radiacion_svg = None
        hsp_svg = None
        costo_svg = None
        panel_svg = None
        proyeccion_svg = None
        
        if chart_payload and sizing_from_items.get('potencia_pico_kwp', 0):
            consumo_data = chart_payload.get('consumo_comparacion', {})
            if consumo_data:
                chart_data['consumo_comparacion'] = {
                    'actual': float(consumo_data.get('actual', 0)),
                    'generacion': float(consumo_data.get('generacion', 0)),
                    'cobertura': float(consumo_data.get('cobertura', 0)),
                    'ahorro_kwh': float(consumo_data.get('ahorro_kwh', 0)),
                }
                # Generate consumption chart SVG
                try:
                    consumo_svg = _generate_consumo_comparison_svg(
                        float(consumo_data.get('actual', 0)),
                        float(consumo_data.get('generacion', 0)),
                        float(consumo_data.get('cobertura', 0))
                    )
                except Exception as e:
                    logger.warning(f"Failed to generate consumption chart SVG: {str(e)}")
            
            chart_data['roi_years'] = proyecto.roi_anos
            chart_data['ahorro_anual'] = float(proyecto.ahorro_mensual or 0) * 12
            chart_data['ahorro_25_anos'] = float(proyecto.ahorro_mensual or 0) * 300
            
            radiacion_mensual = chart_payload.get('radiacion_mensual', [])
            hsp_promedio_valor = float(chart_payload.get('hsp_promedio', proyecto.hsp_promedio or 0))
            
            if radiacion_mensual:
                chart_data['radiacion_mensual'] = radiacion_mensual
                chart_data['radiacion_promedio'] = sum(radiacion_mensual) / len(radiacion_mensual)
                chart_data['hsp_promedio'] = hsp_promedio_valor
                # Generate radiation chart SVG
                try:
                    radiacion_svg = _generate_radiacion_svg(radiacion_mensual)
                except Exception as e:
                    logger.warning(f"Failed to generate radiation chart SVG: {str(e)}")
            
            hsp_mensual = chart_payload.get('hsp_mensual', [])
            if hsp_mensual:
                chart_data['hsp_mensual'] = hsp_mensual
                # Generate HSP chart SVG with average
                try:
                    hsp_svg = _generate_hsp_svg(hsp_mensual, hsp_promedio_valor)
                except Exception as e:
                    logger.warning(f"Failed to generate HSP chart SVG: {str(e)}")
            
            costo_dist = chart_payload.get('costo_por_componente', {})
            if costo_dist.get('labels'):
                chart_data['costo_por_componente'] = costo_dist
                # Generate cost distribution chart SVG
                try:
                    costo_svg = _generate_cost_distribution_svg(
                        costo_dist.get('labels', []),
                        costo_dist.get('values', [])
                    )
                except Exception as e:
                    logger.warning(f"Failed to generate cost distribution chart SVG: {str(e)}")
            
            # Generate financial projection SVG
            proyeccion = chart_payload.get('proyeccion_financiera', {})
            if proyeccion:
                chart_data['proyeccion'] = proyeccion
                try:
                    proyeccion_svg = _generate_proyeccion_financiera_svg(
                        proyeccion.get('anos', list(range(0, 26))),
                        proyeccion.get('ahorro_acumulado', []),
                        float(proyecto.costo_total or 0)
                    )
                except Exception as e:
                    logger.warning(f"Failed to generate financial projection SVG: {str(e)}")
            
            # Generate panel solar SVG
            if panel_area:
                try:
                    panel_svg = _generate_panel_solar_svg(
                        panel_area['largo_mm'],
                        panel_area['ancho_mm'],
                        panel_area['numero_paneles'],
                        panel_area['area_total_m2']
                    )
                except Exception as e:
                    logger.warning(f"Failed to generate panel SVG: {str(e)}")

        # Calculate executive summary metrics
        ahorro_anual = float(proyecto.ahorro_mensual or 0) * 12
        roi_anos = float(proyecto.roi_anos or 0) if proyecto.roi_anos else 0

        # Extract unique equipment categories from items
        categorias_equipos = []
        if items:
            categorias_set = set(item.equipo.get_categoria_display() for item in items)
            categorias_equipos = sorted(list(categorias_set))

        # Build context for template
        context = {
            'cotizacion': cotizacion,
            'cliente': cliente,
            'proyecto': proyecto,
            'items': items,
            'sizing': sizing_from_items,
            'cargas': cargas,
            'panel_area': panel_area,
            'company': company,
            'now': timezone.now(),
            'chart_data': chart_data,
            'consumo_svg': consumo_svg,
            'radiacion_svg': radiacion_svg,
            'hsp_svg': hsp_svg,
            'costo_svg': costo_svg,
            'panel_svg': panel_svg,
            'proyeccion_svg': proyeccion_svg,
            'ahorro_anual': ahorro_anual,
            'roi_anos': roi_anos,
            'categorias_equipos': categorias_equipos,
        }

        # Render HTML template
        html_string = render_to_string('core/cotizaciones/cotizacion_pdf.html', context)
        
        # Convert HTML to PDF using Weasyprint
        html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
        pdf_buffer = html.write_pdf()
        
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="cotizacion_{cotizacion.numero}_weasy.pdf"'
        return response
        
    except Exception as e:
        logger.error(f"Error generating Weasyprint PDF for cotizacion {pk}: {str(e)}", exc_info=True)
        return HttpResponse(f"Error generating PDF: {str(e)}", status=500)


@login_required
def cotizacion_charts_data(request, pk):
    """API endpoint for chart data in cotización view."""
    cotizacion = get_object_or_404(Cotizacion, pk=pk)
    return JsonResponse(build_cotizacion_charts_payload(cotizacion))


# ──────────────────────────────────────────────
# MUNICIPIOS API ENDPOINT
# ──────────────────────────────────────────────

@login_required
def api_municipios_por_departamento(request, departamento_id):
    """AJAX endpoint to fetch municipalities for a given department."""
    try:
        municipios = Municipio.objects.filter(
            departamento_id=departamento_id,
            activo=True
        ).values('id_municipio', 'nombre').order_by('nombre')
        return JsonResponse({
            'municipios': list(municipios)
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ──────────────────────────────────────────────
# COMPANY SETTINGS VIEW
# ──────────────────────────────────────────────

@login_required
def company_settings_view(request):
    """View for editing company configuration (admin only)."""
    if not request.user.is_admin_role and not request.user.is_superuser:
        messages.error(request, 'No tienes permisos de administrador.')
        return redirect('dashboard')

    settings_obj = CompanySettings.load()

    if request.method == 'POST':
        form = CompanySettingsForm(request.POST, request.FILES, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configuración de la empresa actualizada correctamente.')
            return redirect('company_settings')
    else:
        form = CompanySettingsForm(instance=settings_obj)

    return render(request, 'core/settings/company_settings.html', {
        'form': form,
        'settings_obj': settings_obj,
    })


# ──────────────────────────────────────────────
# BACKUP & RESTORE VIEWS
# ──────────────────────────────────────────────

def _restore_sqlite_from_file(backup_file_path: str) -> None:
    """Restore SQLite database from a backup file."""
    db_name = settings.DATABASES["default"].get("NAME")
    if not db_name:
        raise ValueError("SQLite database path is not configured.")

    target_file = Path(db_name)
    target_file.parent.mkdir(parents=True, exist_ok=True)

    # Close Django DB connection before replacing the SQLite file.
    connections["default"].close()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".sqlite3") as tmp_file:
        tmp_path = Path(tmp_file.name)

    try:
        # If the backup file is gzipped, decompress it
        if backup_file_path.endswith('.gz'):
            with gzip.open(backup_file_path, "rb") as src, tmp_path.open("wb") as dst:
                shutil.copyfileobj(src, dst)
        else:
            # Copy directly if not gzipped
            with open(backup_file_path, "rb") as src, tmp_path.open("wb") as dst:
                shutil.copyfileobj(src, dst)
        os.replace(tmp_path, target_file)
    finally:
        tmp_path.unlink(missing_ok=True)


class BackupRestoreView(SuperuserRequiredMixin, ListView):
    """View for restoring database backups (superuser only)."""
    template_name = 'core/settings/backup_restore.html'
    context_object_name = 'form'

    def get_queryset(self):
        # Not used, but required by ListView
        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = BackupRestoreForm()
        return context

    def post(self, request, *args, **kwargs):
        """Handle backup restoration."""
        form = BackupRestoreForm(request.POST, request.FILES)
        
        if form.is_valid():
            backup_file = request.FILES['backup_file']
            
            # Save file temporarily
            temp_path = Path(tempfile.gettempdir()) / backup_file.name
            try:
                # Write uploaded file to temp location
                with open(temp_path, 'wb+') as destination:
                    for chunk in backup_file.chunks():
                        destination.write(chunk)
                
                # Attempt restoration
                engine = settings.DATABASES["default"]["ENGINE"]
                if engine == "django.db.backends.sqlite3":
                    _restore_sqlite_from_file(str(temp_path))
                else:
                    messages.error(
                        request,
                        'Restauración desde interfaz web solo está disponible para SQLite.'
                    )
                    return self.get(request, *args, **kwargs)
                
                messages.success(
                    request,
                    '✅ Base de datos restaurada exitosamente. '
                    'Por favor, recarga la página para aplicar los cambios.'
                )
            except Exception as e:
                messages.error(
                    request,
                    f'❌ Error al restaurar la base de datos: {str(e)}'
                )
            finally:
                # Clean up temp file
                temp_path.unlink(missing_ok=True)
            
            return redirect('backup_restore')
        else:
            context = self.get_context_data(**kwargs)
            context['form'] = form
            return self.render_to_response(context)
