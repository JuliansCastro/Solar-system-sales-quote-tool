"""
Models for Solar Quote App.

Models:
- User: Custom user with roles (admin, seller).
- Cliente: End customer data, consumption, tariff.
- Proyecto: Solar project (on-grid/off-grid).
- Equipo: Equipment inventory with full technical specs.
- Cotizacion: Quote linking project + equipment + pricing.
- CotizacionItem: Individual item in a quote.
- CargaTipo: Catalog of electrical load types.
- Carga: Electrical loads for off-grid sizing (linked to CargaTipo).
"""

import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


# ──────────────────────────────────────────────
# USER MODEL
# ──────────────────────────────────────────────

class User(AbstractUser):
    """Custom user model with roles."""

    class Role(models.TextChoices):
        ADMIN = 'admin', 'Administrador'
        SELLER = 'seller', 'Vendedor'

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.SELLER,
        verbose_name='Rol',
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name='Teléfono')
    company = models.CharField(max_length=200, blank=True, verbose_name='Empresa')

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN

    @property
    def is_seller(self):
        return self.role == self.Role.SELLER


# ──────────────────────────────────────────────
# COMPANY SETTINGS (Singleton)
# ──────────────────────────────────────────────

class CompanySettings(models.Model):
    """Singleton model for company configuration used in reports and UI."""

    name = models.CharField(
        max_length=200, verbose_name='Nombre de la empresa',
        default='Solar Energy Solutions',
    )
    nit = models.CharField(
        max_length=50, blank=True, verbose_name='NIT',
        default='000.000.000-0',
    )
    phone = models.CharField(
        max_length=50, blank=True, verbose_name='Teléfono',
        default='+57 300 000 0000',
    )
    email = models.EmailField(
        blank=True, verbose_name='Correo electrónico',
        default='info@solarenergy.com',
    )
    address = models.CharField(
        max_length=300, blank=True, verbose_name='Dirección',
        default='Bogotá, Colombia',
    )
    logo = models.ImageField(
        upload_to='company/', blank=True, null=True,
        verbose_name='Logo de la empresa',
        help_text='Logo que aparecerá en los reportes PDF y encabezado de la app.',
    )
    website = models.URLField(
        blank=True, verbose_name='Sitio web',
    )
    slogan = models.CharField(
        max_length=200, blank=True, verbose_name='Slogan',
        help_text='Frase que aparece debajo del nombre en el encabezado.',
        default='Herramienta de cotización',
    )

    class Meta:
        verbose_name = 'Configuración de empresa'
        verbose_name_plural = 'Configuración de empresa'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Ensure only one instance exists (singleton pattern)."""
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion of the singleton."""
        pass

    @classmethod
    def load(cls):
        """Load or create the singleton instance."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


# ──────────────────────────────────────────────
# LOCATION MODELS (DEPARTAMENTO & MUNICIPIO)
# ──────────────────────────────────────────────

class Departamento(models.Model):
    """Colombian departments."""

    id_departamento = models.IntegerField(primary_key=True, verbose_name='ID')
    nombre = models.CharField(max_length=255, verbose_name='Departamento')

    class Meta:
        verbose_name = 'Departamento'
        verbose_name_plural = 'Departamentos'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Municipio(models.Model):
    """Colombian municipalities."""

    id_municipio = models.IntegerField(primary_key=True, verbose_name='ID')
    nombre = models.CharField(max_length=255, verbose_name='Municipio')
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.CASCADE,
        related_name='municipios',
        verbose_name='Departamento',
    )
    activo = models.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        verbose_name = 'Municipio'
        verbose_name_plural = 'Municipios'
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} - {self.departamento.nombre}"


# ──────────────────────────────────────────────
# CLIENT MODEL
# ──────────────────────────────────────────────

class Cliente(models.Model):
    """Customer/client information."""

    nombre = models.CharField(max_length=200, verbose_name='Nombre completo')
    email = models.EmailField(verbose_name='Correo electrónico')
    telefono = models.CharField(max_length=20, verbose_name='Teléfono')
    direccion = models.TextField(verbose_name='Dirección')
    
    # Location: ForeignKey to Municipio and Departamento
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.CASCADE,
        verbose_name='Departamento',
        null=True,
        blank=False,
    )
    municipio = models.ForeignKey(
        Municipio,
        on_delete=models.CASCADE,
        verbose_name='Municipio',
        null=True,
        blank=False,
    )

    # Energy consumption data
    consumo_mensual_kwh = models.FloatField(
        verbose_name='Consumo mensual (kWh)',
        validators=[MinValueValidator(0)],
        help_text='Consumo promedio mensual en kWh',
    )
    tarifa_electrica = models.FloatField(
        verbose_name='Tarifa eléctrica (COP/kWh)',
        validators=[MinValueValidator(0)],
        help_text='Tarifa eléctrica en pesos por kWh',
    )
    estrato = models.IntegerField(
        verbose_name='Estrato',
        validators=[MinValueValidator(1), MaxValueValidator(6)],
        default=3,
        help_text='Estrato socioeconómico (1-6)',
    )

    # Metadata
    creado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='clientes', verbose_name='Creado por',
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name='Última actualización')
    notas = models.TextField(blank=True, verbose_name='Notas')

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['-fecha_creacion']

    def __str__(self):
        municipio_nombre = self.municipio.nombre if self.municipio else "Sin municipio"
        return f"{self.nombre} - {municipio_nombre}"

    @property
    def ciudad(self):
        """Backward compatibility property for ciudad field."""
        return self.municipio.nombre if self.municipio else ""

    @property
    def gasto_mensual(self):
        """Monthly energy expenditure in COP."""
        return self.consumo_mensual_kwh * self.tarifa_electrica

    @property
    def consumo_diario_kwh(self):
        """Average daily consumption in kWh."""
        return self.consumo_mensual_kwh / 30


# ──────────────────────────────────────────────
# PROJECT MODEL
# ──────────────────────────────────────────────

class Proyecto(models.Model):
    """Solar project definition."""

    class TipoSistema(models.TextChoices):
        ON_GRID = 'on_grid', 'On-Grid (Conectado a red)'
        OFF_GRID = 'off_grid', 'Off-Grid (Aislado)'
        HYBRID = 'hybrid', 'Híbrido'

    class Estado(models.TextChoices):
        BORRADOR = 'borrador', 'Borrador'
        EN_DISENO = 'en_diseno', 'En diseño'
        COTIZADO = 'cotizado', 'Cotizado'
        APROBADO = 'aprobado', 'Aprobado'
        EN_INSTALACION = 'en_instalacion', 'En instalación'
        COMPLETADO = 'completado', 'Completado'
        CANCELADO = 'cancelado', 'Cancelado'

    # Identification
    codigo = models.CharField(
        max_length=20, unique=True, verbose_name='Código',
        help_text='Código único del proyecto (auto-generado)',
    )
    nombre = models.CharField(max_length=200, verbose_name='Nombre del proyecto')

    # Relationships
    cliente = models.ForeignKey(
        Cliente, on_delete=models.CASCADE,
        related_name='proyectos', verbose_name='Cliente',
    )
    vendedor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='proyectos', verbose_name='Vendedor asignado',
    )

    # System details
    tipo_sistema = models.CharField(
        max_length=10, choices=TipoSistema.choices,
        default=TipoSistema.ON_GRID, verbose_name='Tipo de sistema',
    )
    estado = models.CharField(
        max_length=20, choices=Estado.choices,
        default=Estado.BORRADOR, verbose_name='Estado',
    )

    # Location data
    latitud = models.FloatField(
        verbose_name='Latitud',
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
        default=4.7110,
    )
    longitud = models.FloatField(
        verbose_name='Longitud',
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
        default=-74.0721,
    )
    direccion_instalacion = models.TextField(
        verbose_name='Dirección de instalación', blank=True,
    )

    # Energy consumption from electricity bill
    consumo_mensual_factura_kwh = models.FloatField(
        verbose_name='Consumo mensual factura (kWh)',
        validators=[MinValueValidator(0)],
        null=True, blank=True,
        help_text='Consumo total mensual de la factura de energía (kWh). Si se indica, se usa para dimensionar en lugar del consumo del cliente.',
    )

    # Solar data (from PVGIS or manual)
    hsp_promedio = models.FloatField(
        verbose_name='HSP promedio (horas)',
        validators=[MinValueValidator(0), MaxValueValidator(12)],
        default=4.5,
        help_text='Horas Solar Pico promedio del sitio',
    )
    radiacion_anual = models.FloatField(
        verbose_name='Radiación anual (kWh/m²)',
        validators=[MinValueValidator(0)],
        default=1600,
        help_text='Radiación solar anual en el plano horizontal',
    )

    # Sizing results (calculated)
    potencia_pico_kwp = models.FloatField(
        verbose_name='Potencia pico (kWp)', null=True, blank=True,
    )
    numero_paneles = models.IntegerField(
        verbose_name='Número de paneles', null=True, blank=True,
    )
    generacion_mensual_kwh = models.FloatField(
        verbose_name='Generación mensual estimada (kWh)', null=True, blank=True,
    )
    porcentaje_cobertura = models.FloatField(
        verbose_name='% Cobertura solar', null=True, blank=True,
        help_text='Porcentaje del consumo cubierto por solar',
    )

    # Off-grid specific
    autonomia_dias = models.IntegerField(
        verbose_name='Días de autonomía', default=1,
        validators=[MinValueValidator(1), MaxValueValidator(7)],
        help_text='Días de autonomía del banco de baterías',
    )
    capacidad_baterias_kwh = models.FloatField(
        verbose_name='Capacidad baterías (kWh)', null=True, blank=True,
    )

    # Financial
    costo_total = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        verbose_name='Costo total estimado (COP)',
    )
    ahorro_mensual = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name='Ahorro mensual estimado (COP)',
    )
    roi_anos = models.FloatField(
        verbose_name='Retorno de inversión (años)', null=True, blank=True,
    )

    # Dates
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name='Última actualización')

    class Meta:
        verbose_name = 'Proyecto'
        verbose_name_plural = 'Proyectos'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.codigo} - {self.nombre} ({self.get_tipo_sistema_display()})"

    @property
    def consumo_mensual_efectivo_kwh(self):
        """Monthly consumption used for sizing: bill value or client's value."""
        if self.consumo_mensual_factura_kwh:
            return self.consumo_mensual_factura_kwh
        return self.cliente.consumo_mensual_kwh

    @property
    def consumo_diario_kwh(self):
        """Average daily consumption in kWh (from bill or client data)."""
        return round(self.consumo_mensual_efectivo_kwh / 30, 2)

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = self._generate_code()
        super().save(*args, **kwargs)

    def _generate_code(self):
        prefix = 'SOL'
        date_part = timezone.now().strftime('%y%m')
        last = Proyecto.objects.filter(
            codigo__startswith=f'{prefix}-{date_part}'
        ).order_by('-codigo').first()
        if last:
            try:
                last_num = int(last.codigo.split('-')[-1])
            except (ValueError, IndexError):
                last_num = 0
            return f"{prefix}-{date_part}-{last_num + 1:04d}"
        return f"{prefix}-{date_part}-0001"


# ──────────────────────────────────────────────
# EQUIPO (EQUIPMENT INVENTORY) MODEL
# ──────────────────────────────────────────────

class Equipo(models.Model):
    """Equipment inventory with full technical specifications."""

    class Categoria(models.TextChoices):
        PANEL = 'panel', 'Panel Solar'
        INVERSOR = 'inversor', 'Inversor'
        BATERIA = 'bateria', 'Batería'
        REGULADOR = 'regulador', 'Regulador de carga'
        ESTRUCTURA = 'estructura', 'Estructura de montaje'
        CABLE = 'cable', 'Cableado'
        PROTECCION = 'proteccion', 'Protección eléctrica'
        MEDIDOR = 'medidor', 'Medidor bidireccional'
        ACCESORIO = 'accesorio', 'Accesorio'
        OTRO = 'otro', 'Otro'

    class TipoSistemaCompatible(models.TextChoices):
        ON_GRID = 'on_grid', 'On-Grid'
        OFF_GRID = 'off_grid', 'Off-Grid'
        AMBOS = 'ambos', 'Ambos'

    # Basic info
    nombre = models.CharField(max_length=200, verbose_name='Nombre')
    modelo = models.CharField(max_length=100, verbose_name='Modelo')
    fabricante = models.CharField(max_length=100, verbose_name='Fabricante')
    categoria = models.CharField(
        max_length=20, choices=Categoria.choices, verbose_name='Categoría',
    )
    sku = models.CharField(
        max_length=50, unique=True, verbose_name='SKU',
        help_text='Código único de referencia',
    )
    descripcion = models.TextField(blank=True, verbose_name='Descripción técnica')

    # Technical specifications
    potencia_nominal_w = models.FloatField(
        verbose_name='Potencia nominal (W)',
        validators=[MinValueValidator(0)],
        help_text='Potencia nominal en Watts',
    )
    voltaje_nominal = models.FloatField(
        verbose_name='Voltaje nominal (V)',
        validators=[MinValueValidator(0)],
        null=True, blank=True,
    )
    corriente_nominal = models.FloatField(
        verbose_name='Corriente nominal (A)',
        validators=[MinValueValidator(0)],
        null=True, blank=True,
    )
    eficiencia = models.FloatField(
        verbose_name='Eficiencia (%)',
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        null=True, blank=True,
    )
    datos_tecnicos = models.JSONField(
        verbose_name='Datos técnicos adicionales',
        default=dict, blank=True,
        help_text='Datos técnicos en formato JSON (Voc, Isc, MPPT range, etc.)',
    )
    sistema_compatible = models.CharField(
        max_length=10, choices=TipoSistemaCompatible.choices,
        default=TipoSistemaCompatible.AMBOS,
        verbose_name='Sistema compatible',
    )

    # Physical specs
    garantia_anos = models.IntegerField(
        verbose_name='Garantía (años)',
        validators=[MinValueValidator(0)],
        default=1,
    )
    largo_mm = models.FloatField(
        verbose_name='Largo (mm)', null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    ancho_mm = models.FloatField(
        verbose_name='Ancho (mm)', null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    alto_mm = models.FloatField(
        verbose_name='Alto (mm)', null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    peso_kg = models.FloatField(
        verbose_name='Peso (kg)', null=True, blank=True,
        validators=[MinValueValidator(0)],
    )

    # Pricing and stock
    precio_proveedor = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name='Precio proveedor (COP)',
        validators=[MinValueValidator(0)],
    )
    precio_venta = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name='Precio venta (COP)',
        validators=[MinValueValidator(0)],
    )
    margen_porcentaje = models.FloatField(
        verbose_name='Margen (%)',
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=30,
    )
    stock = models.IntegerField(
        verbose_name='Stock disponible',
        validators=[MinValueValidator(0)],
        default=0,
    )
    fecha_actualizacion_precio = models.DateField(
        verbose_name='Última actualización de precio',
        default=timezone.now,
    )

    # Files
    imagen = models.ImageField(
        upload_to='equipos/imagenes/', blank=True, null=True,
        verbose_name='Imagen',
    )
    ficha_tecnica = models.FileField(
        upload_to='equipos/fichas/', blank=True, null=True,
        verbose_name='Ficha técnica (PDF)',
    )

    # Metadata
    activo = models.BooleanField(default=True, verbose_name='Activo')
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name='Última actualización')

    class Meta:
        verbose_name = 'Equipo'
        verbose_name_plural = 'Equipos'
        ordering = ['categoria', 'fabricante', 'nombre']

    def __str__(self):
        return f"{self.fabricante} {self.modelo} - {self.potencia_nominal_w}W"

    @property
    def dimensiones(self):
        """Return dimensions as string LxWxH."""
        parts = []
        if self.largo_mm:
            parts.append(f"{self.largo_mm:.0f}")
        if self.ancho_mm:
            parts.append(f"{self.ancho_mm:.0f}")
        if self.alto_mm:
            parts.append(f"{self.alto_mm:.0f}")
        return ' x '.join(parts) + ' mm' if parts else 'N/A'

    @property
    def en_stock(self):
        return self.stock > 0


# ──────────────────────────────────────────────
# QUOTE MODEL
# ──────────────────────────────────────────────

class Cotizacion(models.Model):
    """Quote / price estimate for a project."""

    class Estado(models.TextChoices):
        BORRADOR = 'borrador', 'Borrador'
        ENVIADA = 'enviada', 'Enviada al cliente'
        APROBADA = 'aprobada', 'Aprobada'
        RECHAZADA = 'rechazada', 'Rechazada'
        VENCIDA = 'vencida', 'Vencida'

    class TipoCliente(models.TextChoices):
        FINAL = 'final', 'Cliente final'
        INSTALADOR = 'instalador', 'Instalador'
        DISTRIBUIDOR = 'distribuidor', 'Distribuidor'

    # Identification
    numero = models.CharField(
        max_length=20, unique=True, verbose_name='Número de cotización',
    )
    proyecto = models.ForeignKey(
        Proyecto, on_delete=models.CASCADE,
        related_name='cotizaciones', verbose_name='Proyecto',
    )

    # Status
    estado = models.CharField(
        max_length=15, choices=Estado.choices,
        default=Estado.BORRADOR, verbose_name='Estado',
    )
    tipo_cliente = models.CharField(
        max_length=15, choices=TipoCliente.choices,
        default=TipoCliente.FINAL, verbose_name='Tipo de cliente',
    )

    # Financial
    subtotal = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        verbose_name='Subtotal (COP)',
    )
    descuento_porcentaje = models.FloatField(
        default=0, verbose_name='Descuento (%)',
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    descuento_monto = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        verbose_name='Descuento (COP)',
    )
    iva_porcentaje = models.FloatField(
        default=19.0, verbose_name='IVA (%)',
    )
    iva_monto = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        verbose_name='IVA (COP)',
    )
    total = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        verbose_name='Total (COP)',
    )

    # Manual total override
    usar_total_manual = models.BooleanField(
        default=False, verbose_name='Usar total manual',
        help_text='Permite ingresar el valor total directamente sin desglosar ítems.',
    )
    total_manual = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        verbose_name='Total manual (COP)',
        help_text='Valor total del proyecto ingresado manualmente.',
    )

    # Installation costs
    costo_instalacion = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Costo de instalación (COP)',
    )
    costo_transporte = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Costo de transporte (COP)',
    )

    # Validity
    fecha_emision = models.DateField(
        default=timezone.now, verbose_name='Fecha de emisión',
    )
    dias_validez = models.IntegerField(
        default=30, verbose_name='Días de validez',
    )
    condiciones = models.TextField(
        blank=True, verbose_name='Condiciones y notas',
        default=(
            '• Precios sujetos a cambio sin previo aviso.\n'
            '• Validez de la cotización: 5 días calendario.\n'
            '• Garantía según fabricante de cada equipo.\n'
            '• Tiempo de entrega: 1 - 5 días hábiles según disponibilidad.'
        ),
    )

    # Created by
    creado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='cotizaciones', verbose_name='Creado por',
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name='Última actualización')

    class Meta:
        verbose_name = 'Cotización'
        verbose_name_plural = 'Cotizaciones'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Cotización {self.numero} - {self.proyecto.nombre}"

    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = self._generate_number()
        super().save(*args, **kwargs)

    def _generate_number(self):
        # Prefix: primeros 3 caracteres del nombre del vendedor
        if self.creado_por and self.creado_por.first_name:
            prefix = self.creado_por.first_name[:3].upper()
        elif self.creado_por:
            prefix = self.creado_por.username[:3].upper()
        else:
            prefix = 'USR'
        
        # Date part: YYMMDD
        date_part = timezone.now().strftime('%y%m%d')
        search_pattern = f'{prefix}-{date_part}'
        
        last = Cotizacion.objects.filter(
            numero__startswith=search_pattern
        ).order_by('-numero').first()
        
        if last:
            try:
                last_num = int(last.numero.split('-')[-1])
            except (ValueError, IndexError):
                last_num = 0
            return f"{prefix}-{date_part}-{last_num + 1:03d}"
        return f"{prefix}-{date_part}-001"

    def calcular_totales(self):
        """Recalculate subtotal, discounts, tax, and total.

        If ``usar_total_manual`` is True and ``total_manual`` has a value the
        total is set directly from the manual input and the intermediate
        financial fields (subtotal, descuento_monto, iva_monto) are derived
        backwards so reports and detail views stay consistent.
        """
        if self.usar_total_manual and self.total_manual is not None:
            self.total = self.total_manual
            # Derive backwards so the detail view / PDF still shows coherent numbers
            iva_pct = Decimal(str(self.iva_porcentaje)) / Decimal('100')
            # total = subtotal_neto + iva  →  subtotal_neto = total / (1 + iva_pct)
            subtotal_neto = self.total / (Decimal('1') + iva_pct)
            self.iva_monto = self.total - subtotal_neto
            self.descuento_monto = Decimal('0')
            self.subtotal = subtotal_neto
            self.save()
            return

        items = self.items.all()
        subtotal_gravado = sum(item.subtotal for item in items if item.aplica_iva)
        subtotal_exento = sum(item.subtotal for item in items if not item.aplica_iva)
        self.subtotal = subtotal_gravado + subtotal_exento

        # Add installation and transport (considered gravado)
        self.subtotal += self.costo_instalacion + self.costo_transporte
        subtotal_gravado += self.costo_instalacion + self.costo_transporte

        # Discount applied proportionally
        desc_pct = Decimal(str(self.descuento_porcentaje)) / Decimal('100')
        self.descuento_monto = self.subtotal * desc_pct
        base_con_descuento = self.subtotal - self.descuento_monto

        # IVA only on gravado portion after discount
        gravado_con_descuento = subtotal_gravado * (Decimal('1') - desc_pct)
        self.iva_monto = gravado_con_descuento * (Decimal(str(self.iva_porcentaje)) / Decimal('100'))

        # Total
        self.total = base_con_descuento + self.iva_monto
        self.save()

    @property
    def fecha_vencimiento(self):
        from datetime import timedelta
        return self.fecha_emision + timedelta(days=self.dias_validez)


class CotizacionItem(models.Model):
    """Individual line item in a quote."""

    cotizacion = models.ForeignKey(
        Cotizacion, on_delete=models.CASCADE,
        related_name='items', verbose_name='Cotización',
    )
    equipo = models.ForeignKey(
        Equipo, on_delete=models.PROTECT,
        related_name='cotizacion_items', verbose_name='Equipo',
    )
    cantidad = models.IntegerField(
        verbose_name='Cantidad',
        validators=[MinValueValidator(1)],
        default=1,
    )
    precio_unitario = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Precio unitario (COP)',
    )
    descuento_item = models.FloatField(
        default=0, verbose_name='Descuento item (%)',
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    aplica_iva = models.BooleanField(
        default=True, verbose_name='IVA',
        help_text='Marcar si este ítem aplica IVA',
    )

    class Meta:
        verbose_name = 'Item de cotización'
        verbose_name_plural = 'Items de cotización'

    def __str__(self):
        return f"{self.cantidad}x {self.equipo.nombre}"

    @property
    def subtotal(self):
        precio = self.precio_unitario * self.cantidad
        descuento = precio * (Decimal(str(self.descuento_item)) / Decimal('100'))
        return precio - descuento


# ──────────────────────────────────────────────
# LOAD CATALOG MODEL
# ──────────────────────────────────────────────

class CargaTipo(models.Model):
    """Catalog of electrical load types with default specs."""

    class Categoria(models.TextChoices):
        ILUMINACION = 'iluminacion', 'Iluminación'
        ELECTRODOMESTICO = 'electrodomestico', 'Electrodoméstico'
        CLIMATIZACION = 'climatizacion', 'Climatización'
        BOMBEO = 'bombeo', 'Bombeo'
        HERRAMIENTA = 'herramienta', 'Herramienta'
        COMUNICACION = 'comunicacion', 'Comunicación'
        OTRO = 'otro', 'Otro'

    nombre = models.CharField(
        max_length=200, verbose_name='Nombre del dispositivo',
        help_text='Ej: Refrigerador, TV LED 42", Bombillo LED 9W',
    )
    categoria = models.CharField(
        max_length=20, choices=Categoria.choices,
        default=Categoria.OTRO, verbose_name='Categoría',
    )
    potencia_nominal_w = models.FloatField(
        verbose_name='Potencia nominal (W)',
        validators=[MinValueValidator(0)],
    )
    horas_uso_dia = models.FloatField(
        verbose_name='Horas de uso por día (por defecto)',
        validators=[MinValueValidator(0), MaxValueValidator(24)],
        default=1.0,
    )
    factor_potencia = models.FloatField(
        verbose_name='Factor de potencia',
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        default=1.0,
        help_text='1.0 para cargas resistivas, < 1.0 para cargas inductivas',
    )
    carga_reactiva = models.BooleanField(
        default=False, verbose_name='Carga reactiva',
        help_text='Marcar si el dispositivo tiene motor (refrigerador, bomba, etc.)',
    )
    factor_arranque = models.FloatField(
        verbose_name='Factor de arranque',
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        default=1.0,
        help_text='Multiplicador de potencia al arranque (3-5 para motores)',
    )
    descripcion = models.TextField(
        blank=True, verbose_name='Descripción / Notas',
    )
    activo = models.BooleanField(default=True, verbose_name='Activo')
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name='Última actualización')

    class Meta:
        verbose_name = 'Tipo de carga'
        verbose_name_plural = 'Tipos de cargas'
        ordering = ['categoria', 'nombre']

    def __str__(self):
        return f"{self.nombre} ({self.potencia_nominal_w}W)"


# ──────────────────────────────────────────────
# ELECTRICAL LOAD MODEL
# ──────────────────────────────────────────────

class Carga(models.Model):
    """Electrical load for off-grid system sizing."""

    class Prioridad(models.TextChoices):
        ESENCIAL = 'esencial', 'Esencial'
        IMPORTANTE = 'importante', 'Importante'
        OPCIONAL = 'opcional', 'Opcional'

    proyecto = models.ForeignKey(
        Proyecto, on_delete=models.CASCADE,
        related_name='cargas', verbose_name='Proyecto',
    )
    tipo_carga = models.ForeignKey(
        CargaTipo, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='cargas', verbose_name='Tipo de carga',
        help_text='Seleccionar de la lista predefinida',
    )

    dispositivo = models.CharField(
        max_length=200, verbose_name='Dispositivo',
        help_text='Ej: Refrigerador, TV, Iluminación LED',
    )
    cantidad = models.IntegerField(
        verbose_name='Cantidad',
        validators=[MinValueValidator(1)],
        default=1,
    )
    potencia_nominal_w = models.FloatField(
        verbose_name='Potencia nominal (W)',
        validators=[MinValueValidator(0)],
    )
    horas_uso_dia = models.FloatField(
        verbose_name='Horas de uso por día',
        validators=[MinValueValidator(0), MaxValueValidator(24)],
    )
    factor_potencia = models.FloatField(
        verbose_name='Factor de potencia',
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        default=1.0,
        help_text='1.0 para cargas resistivas, < 1.0 para cargas inductivas',
    )
    carga_reactiva = models.BooleanField(
        default=False, verbose_name='Carga reactiva',
        help_text='Marcar si el dispositivo tiene motor (refrigerador, bomba, etc.)',
    )
    factor_arranque = models.FloatField(
        verbose_name='Factor de arranque',
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        default=1.0,
        help_text='Multiplicador de potencia al arranque (3-5 para motores)',
    )
    prioridad = models.CharField(
        max_length=15, choices=Prioridad.choices,
        default=Prioridad.IMPORTANTE, verbose_name='Prioridad',
    )

    class Meta:
        verbose_name = 'Carga'
        verbose_name_plural = 'Cargas'
        ordering = ['prioridad', 'dispositivo']

    def __str__(self):
        return f"{self.dispositivo} ({self.potencia_nominal_w}W x {self.cantidad})"

    @property
    def potencia_total_w(self):
        """Total power for this load."""
        return self.potencia_nominal_w * self.cantidad

    @property
    def energia_diaria_wh(self):
        """Daily energy consumption in Wh."""
        return self.potencia_total_w * self.horas_uso_dia

    @property
    def potencia_arranque_w(self):
        """Startup power (for reactive loads)."""
        return self.potencia_total_w * self.factor_arranque

    @property
    def potencia_aparente_va(self):
        """Apparent power in VA."""
        if self.factor_potencia > 0:
            return self.potencia_total_w / self.factor_potencia
        return self.potencia_total_w


# ──────────────────────────────────────────────
# EQUIPMENT SELECTION MODELS
# ──────────────────────────────────────────────

class SelectedEquipo(models.Model):
    """Equipment selected for a specific project during sizing.
    
    Tracks which equipment (panels, inverters, etc.) the user has selected
    for a project, allowing real-time recalculation of generation based on
    actual equipment specs.
    """

    class TipoEquipo(models.TextChoices):
        PANEL = 'panel', 'Panel Solar'
        INVERSOR = 'inversor', 'Inversor'
        ESTRUCTURA = 'estructura', 'Estructura'
        REGULADOR = 'regulador', 'Regulador de carga'
        BATERIA = 'bateria', 'Batería'
        OTRO = 'otro', 'Otro'

    # Relationships
    proyecto = models.ForeignKey(
        Proyecto, on_delete=models.CASCADE,
        related_name='equipos_seleccionados', verbose_name='Proyecto',
    )
    equipo = models.ForeignKey(
        Equipo, on_delete=models.PROTECT,
        related_name='selecciones', verbose_name='Equipo',
    )

    # Selection details
    tipo_equipo = models.CharField(
        max_length=20, choices=TipoEquipo.choices,
        verbose_name='Tipo de equipo',
    )
    cantidad = models.IntegerField(
        verbose_name='Cantidad',
        validators=[MinValueValidator(1)],
        default=1,
    )
    notas = models.TextField(
        blank=True, verbose_name='Notas',
        help_text='Notas adicionales sobre esta selección',
    )

    # Calculated fields (cached)
    perdidas_estimadas_porcentaje = models.FloatField(
        null=True, blank=True, verbose_name='Pérdidas estimadas (%)',
        help_text='Pérdidas estimadas basadas en especificaciones del equipo',
    )
    generacion_afectada_kwh = models.FloatField(
        null=True, blank=True, verbose_name='Generación afectada (kWh)',
        help_text='Impacto en generación mensual por este componente',
    )

    # Metadata
    fecha_seleccion = models.DateTimeField(
        auto_now_add=True, verbose_name='Fecha de selección',
    )
    fecha_actualizacion = models.DateTimeField(
        auto_now=True, verbose_name='Última actualización',
    )
    activo = models.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        verbose_name = 'Equipo seleccionado'
        verbose_name_plural = 'Equipos seleccionados'
        unique_together = ('proyecto', 'equipo', 'tipo_equipo')
        ordering = ['tipo_equipo', 'equipo__fabricante', 'equipo__modelo']

    def __str__(self):
        return f"{self.proyecto.codigo} - {self.cantidad}x {self.equipo.nombre}"

    @property
    def potencia_total(self):
        """Total power from this equipment selection."""
        return self.equipo.potencia_nominal_w * self.cantidad

    @property
    def subtotal_equipo(self):
        """Equipment cost for this selection."""
        return float(self.equipo.precio_venta) * self.cantidad


class EquipoCompatibilidad(models.Model):
    """Track compatibility rules and conflicts between equipment types.
    
    Stores validation rules for equipment compatibility (e.g., voltage matching
    between panels and inverters, string sizing rules, etc.).
    """

    class TipoValidacion(models.TextChoices):
        VOLTAJE = 'voltaje', 'Rango de voltaje'
        CORRIENTE = 'corriente', 'Rango de corriente'
        POTENCIA = 'potencia', 'Rango de potencia'
        TECNOLOGIA = 'tecnologia', 'Compatibilidad de tecnología'
        CUSTOM = 'custom', 'Validación personalizada'

    # Define compatibility rule
    equipo_base = models.ForeignKey(
        Equipo, on_delete=models.CASCADE,
        related_name='compatibilidades_como_base',
        verbose_name='Equipo base',
    )
    equipo_compatible = models.ForeignKey(
        Equipo, on_delete=models.CASCADE,
        related_name='compatibilidades_como_compatible',
        verbose_name='Equipo compatible',
    )

    # Validation type
    tipo_validacion = models.CharField(
        max_length=20, choices=TipoValidacion.choices,
        default=TipoValidacion.VOLTAJE,
        verbose_name='Tipo de validación',
    )

    # Constraints
    valor_minimo = models.FloatField(
        null=True, blank=True, verbose_name='Valor mínimo',
    )
    valor_maximo = models.FloatField(
        null=True, blank=True, verbose_name='Valor máximo',
    )
    mensaje_alerta = models.TextField(
        blank=True, verbose_name='Mensaje de alerta',
        help_text='Mensaje mostrado si se incumple la validación',
    )
    es_critico = models.BooleanField(
        default=False, verbose_name='Es crítico',
        help_text='Si es crítico, impide guardar la combinación',
    )

    # Metadata
    activo = models.BooleanField(default=True, verbose_name='Activo')
    fecha_creacion = models.DateTimeField(
        auto_now_add=True, verbose_name='Fecha de creación',
    )

    class Meta:
        verbose_name = 'Compatibilidad de equipos'
        verbose_name_plural = 'Compatibilidades de equipos'
        unique_together = ('equipo_base', 'equipo_compatible', 'tipo_validacion')

    def __str__(self):
        return f"{self.equipo_base.nombre} + {self.equipo_compatible.nombre}"


class ChartExplanation(models.Model):
    """Persuasive explanations for charts used in PDF reports and UI.
    
    Stores editable, persuasive descriptions for each chart that help
    clients understand the benefits and technical details of their system.
    """

    class TipoGrafico(models.TextChoices):
        CONSUMO_VS_GENERACION = 'consumo_generacion', 'Consumo vs Generación'
        ROI_ACUMULADO = 'roi_acumulado', 'ROI Acumulado'
        RADIACION_MENSUAL = 'radiacion_mensual', 'Radiación mensual (PVGIS)'
        HSP_MENSUAL = 'hsp_mensual', 'HSP - Horas Solar Pico'
        EFICIENCIA_SISTEMA = 'eficiencia', 'Eficiencia del sistema'
        PERDIDAS_SISTEMA = 'perdidas', 'Pérdidas del sistema'

    # Link to project sizing
    proyecto = models.OneToOneField(
        Proyecto, on_delete=models.CASCADE,
        related_name='chart_explanations',
        null=True, blank=True,
        verbose_name='Proyecto',
    )

    # Chart type
    tipo_grafico = models.CharField(
        max_length=30, choices=TipoGrafico.choices,
        verbose_name='Tipo de gráfico',
    )

    # Explanations
    titulo_corto = models.CharField(
        max_length=150, verbose_name='Título corto',
        help_text='Título del gráfico en lo UI',
    )
    explicacion_tecnica = models.TextField(
        verbose_name='Explicación técnica',
        help_text='Explicación detallada para el PDF (3-5 párrafos)',
    )
    puntos_clave = models.TextField(
        verbose_name='Puntos clave',
        help_text='Lista de puntos clave separados por líneas',
    )
    recomendaciones = models.TextField(
        blank=True, verbose_name='Recomendaciones',
        help_text='Recomendaciones para el usuario (opcional)',
    )

    # Customization
    es_personalizada = models.BooleanField(
        default=False, verbose_name='Es personalizada',
        help_text='Si es False, usa la explicación por defecto del sistema',
    )

    # Metadata
    fecha_creacion = models.DateTimeField(
        auto_now_add=True, verbose_name='Fecha de creación',
    )
    fecha_actualizacion = models.DateTimeField(
        auto_now=True, verbose_name='Última actualización',
    )

    class Meta:
        verbose_name = 'Explicación de gráfico'
        verbose_name_plural = 'Explicaciones de gráficos'
        ordering = ['tipo_grafico']

    def __str__(self):
        return f"{self.get_tipo_grafico_display()} - {self.titulo_corto}"
