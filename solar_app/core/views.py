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
from django.utils import timezone

from .models import (
    User, Cliente, Proyecto, Equipo, Cotizacion, CotizacionItem, Carga, CargaTipo,
    CompanySettings,
)
from .forms import (
    CustomLoginForm, UserRegistrationForm,
    ClienteForm, ProyectoForm, EquipoForm, EquipoFilterForm,
    CotizacionForm, CotizacionItemFormSet, CargaForm, CargaFormSet,
    CargaTipoForm, CompanySettingsForm,
)
from .sizing import (
    dimensionar_on_grid, dimensionar_off_grid, obtener_datos_pvgis,
    sugerir_equipos, calcular_proyeccion_financiera,
)


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

    context = {
        'proyecto': proyecto,
        'cliente': cliente,
        'resultado': resultado,
        'sugerencias': sugerencias,
        'pvgis_data': pvgis_data,
        'proyeccion': json.dumps(proyeccion) if proyeccion else None,
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


class EquipoCreateView(LoginRequiredMixin, CreateView):
    model = Equipo
    form_class = EquipoForm
    template_name = 'core/equipos/equipo_form.html'
    success_url = reverse_lazy('equipo_list')

    def form_valid(self, form):
        messages.success(self.request, 'Equipo agregado al inventario.')
        return super().form_valid(form)


class EquipoUpdateView(LoginRequiredMixin, UpdateView):
    model = Equipo
    form_class = EquipoForm
    template_name = 'core/equipos/equipo_form.html'
    success_url = reverse_lazy('equipo_list')

    def form_valid(self, form):
        form.instance.fecha_actualizacion_precio = timezone.now().date()
        messages.success(self.request, 'Equipo actualizado.')
        return super().form_valid(form)


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
    return redirect('equipo_detail', pk=nuevo.pk)


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
    """Create a quote pre-filled with sizing results."""
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

    # Get suggestions and add items
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

    cotizacion.calcular_totales()
    proyecto.estado = 'cotizado'
    proyecto.save()

    messages.success(request, f'Cotización {cotizacion.numero} creada con equipos sugeridos.')
    return redirect('cotizacion_detail', pk=cotizacion.pk)


# ──────────────────────────────────────────────
# REPORT VIEWS
# ──────────────────────────────────────────────

@login_required
def cotizacion_pdf(request, pk):
    """Generate PDF report for a quote."""
    from .reports import generar_pdf_cotizacion

    cotizacion = get_object_or_404(Cotizacion, pk=pk)
    pdf_buffer = generar_pdf_cotizacion(cotizacion)

    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="cotizacion_{cotizacion.numero}.pdf"'
    return response


@login_required
def cotizacion_excel(request, pk):
    """Generate Excel report for a quote."""
    from .reports import generar_excel_cotizacion

    cotizacion = get_object_or_404(Cotizacion, pk=pk)
    excel_buffer = generar_excel_cotizacion(cotizacion)

    response = HttpResponse(
        excel_buffer,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="cotizacion_{cotizacion.numero}.xlsx"'
    return response


@login_required
def cotizacion_charts_data(request, pk):
    """API endpoint for chart data in cotización view."""
    cotizacion = get_object_or_404(Cotizacion, pk=pk)
    proyecto = cotizacion.proyecto
    cliente = proyecto.cliente

    # Cost distribution by category
    items = cotizacion.items.select_related('equipo').all()
    cost_by_category = {}
    for item in items:
        cat = item.equipo.get_categoria_display()
        cost_by_category[cat] = cost_by_category.get(cat, 0) + float(item.subtotal)

    if float(cotizacion.costo_instalacion) > 0:
        cost_by_category['Instalación'] = float(cotizacion.costo_instalacion)
    if float(cotizacion.costo_transporte) > 0:
        cost_by_category['Transporte'] = float(cotizacion.costo_transporte)

    # Consumption comparison
    generacion = proyecto.generacion_mensual_kwh or 0
    consumo = cliente.consumo_mensual_kwh

    # Financial projection
    ahorro_anual = float(proyecto.ahorro_mensual or 0) * 12
    costo = float(proyecto.costo_total or 0)

    proyeccion = calcular_proyeccion_financiera(
        ahorro_anual_cop=ahorro_anual,
        costo_sistema=costo,
    )

    # Monthly savings comparison
    gasto_actual = consumo * cliente.tarifa_electrica
    gasto_con_solar = max(0, (consumo - generacion)) * cliente.tarifa_electrica

    # PVGIS data for radiation and HSP charts
    pvgis_data = obtener_datos_pvgis(proyecto.latitud, proyecto.longitud)
    radiacion_mensual = []
    hsp_mensual = []
    if pvgis_data.radiacion_mensual:
        radiacion_mensual = [r['radiacion_kwh_m2'] for r in pvgis_data.radiacion_mensual]
        hsp_mensual = [r['hsp'] for r in pvgis_data.radiacion_mensual]

    return JsonResponse({
        'costo_por_componente': {
            'labels': list(cost_by_category.keys()),
            'values': list(cost_by_category.values()),
        },
        'consumo_comparacion': {
            'labels': ['Consumo actual', 'Con sistema solar'],
            'actual': consumo,
            'con_solar': max(0, consumo - generacion),
            'generacion': generacion,
        },
        'ahorro_dinero': {
            'gasto_actual': gasto_actual,
            'gasto_con_solar': gasto_con_solar,
            'ahorro_mensual': gasto_actual - gasto_con_solar,
        },
        'proyeccion_financiera': proyeccion,
        'roi_anos': proyecto.roi_anos,
        'radiacion_mensual': radiacion_mensual,
        'hsp_mensual': hsp_mensual,
        'hsp_promedio': pvgis_data.hsp_promedio,
        'sizing': {
            'potencia_pico_kwp': proyecto.potencia_pico_kwp,
            'numero_paneles': proyecto.numero_paneles,
            'generacion_mensual_kwh': generacion,
            'porcentaje_cobertura': proyecto.porcentaje_cobertura,
            'capacidad_baterias_kwh': proyecto.capacidad_baterias_kwh,
            'autonomia_dias': proyecto.autonomia_dias,
        },
    })


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
