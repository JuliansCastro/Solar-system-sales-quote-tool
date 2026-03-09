"""
Forms for Solar Quote App.

Includes forms for all CRUD operations with proper validations.
"""

from decimal import Decimal

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from .models import User, Cliente, Proyecto, Equipo, Cotizacion, CotizacionItem, Carga, CargaTipo, CompanySettings


# ──────────────────────────────────────────────
# COMPANY SETTINGS FORM
# ──────────────────────────────────────────────

class CompanySettingsForm(forms.ModelForm):
    """Form for editing company settings."""

    class Meta:
        model = CompanySettings
        fields = [
            'name', 'nit', 'phone', 'email', 'address',
            'logo', 'website', 'slogan',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Nombre de la empresa',
            }),
            'nit': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '000.000.000-0',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '+57 300 000 0000',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'info@empresa.com',
            }),
            'address': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Dirección completa',
            }),
            'logo': forms.ClearableFileInput(attrs={
                'class': 'form-input',
                'accept': 'image/*',
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-input',
                'placeholder': 'https://www.empresa.com',
            }),
            'slogan': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Frase o slogan de la empresa',
            }),
        }


# ──────────────────────────────────────────────
# AUTH FORMS
# ──────────────────────────────────────────────

class CustomLoginForm(AuthenticationForm):
    """Custom login form with Tailwind styling."""

    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500',
            'placeholder': 'Usuario',
            'autofocus': True,
        }),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500',
            'placeholder': 'Contraseña',
        }),
    )


class UserRegistrationForm(UserCreationForm):
    """User registration form."""

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'phone', 'company')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-input'}),
            'company': forms.TextInput(attrs={'class': 'form-input'}),
        }


# ──────────────────────────────────────────────
# CLIENT FORMS
# ──────────────────────────────────────────────

class ClienteForm(forms.ModelForm):
    """Form for creating/editing clients."""

    class Meta:
        model = Cliente
        fields = [
            'nombre', 'email', 'telefono', 'direccion', 'ciudad',
            'departamento', 'consumo_mensual_kwh', 'tarifa_electrica',
            'estrato', 'notas',
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Nombre completo del cliente',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'correo@ejemplo.com',
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '+57 300 000 0000',
            }),
            'direccion': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 2,
                'placeholder': 'Dirección completa',
            }),
            'ciudad': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ciudad',
            }),
            'departamento': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Departamento',
            }),
            'consumo_mensual_kwh': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': '300',
                'step': '0.1',
                'min': '0',
            }),
            'tarifa_electrica': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': '750',
                'step': '0.01',
                'min': '0',
            }),
            'estrato': forms.Select(
                choices=[(i, f'Estrato {i}') for i in range(1, 7)],
                attrs={'class': 'form-select'},
            ),
            'notas': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 3,
                'placeholder': 'Notas adicionales...',
            }),
        }


# ──────────────────────────────────────────────
# PROYECTO FORMS
# ──────────────────────────────────────────────

class ProyectoForm(forms.ModelForm):
    """Form for creating/editing projects."""

    class Meta:
        model = Proyecto
        fields = [
            'nombre', 'cliente', 'tipo_sistema', 'latitud', 'longitud',
            'direccion_instalacion', 'consumo_mensual_factura_kwh',
            'hsp_promedio', 'autonomia_dias',
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Nombre del proyecto',
            }),
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'tipo_sistema': forms.Select(attrs={'class': 'form-select'}),
            'latitud': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': 'any',
                'placeholder': '4.7110',
            }),
            'longitud': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': 'any',
                'placeholder': '-74.0721',
            }),
            'direccion_instalacion': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 2,
                'placeholder': 'Dirección del sitio de instalación',
            }),
            'consumo_mensual_factura_kwh': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.1',
                'min': '0',
                'placeholder': 'Ej: 350',
            }),
            'hsp_promedio': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0',
                'max': '12',
                'placeholder': '4.50',
            }),
            'autonomia_dias': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '1',
                'max': '7',
                'placeholder': '1',
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and user.is_seller:
            self.fields['cliente'].queryset = Cliente.objects.filter(creado_por=user)


# ──────────────────────────────────────────────
# EQUIPO (INVENTORY) FORMS
# ──────────────────────────────────────────────

class EquipoForm(forms.ModelForm):
    """Form for equipment CRUD with full validation."""

    class Meta:
        model = Equipo
        fields = [
            'nombre', 'modelo', 'fabricante', 'categoria', 'sku',
            'descripcion', 'potencia_nominal_w', 'voltaje_nominal',
            'corriente_nominal', 'eficiencia', 'sistema_compatible',
            'garantia_anos', 'largo_mm', 'ancho_mm', 'alto_mm', 'peso_kg',
            'precio_proveedor', 'precio_venta', 'margen_porcentaje',
            'stock', 'imagen', 'ficha_tecnica', 'activo',
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Nombre del equipo'}),
            'modelo': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Modelo'}),
            'fabricante': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Fabricante'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'sku': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'SKU-001'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'potencia_nominal_w': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.1', 'min': '0'}),
            'voltaje_nominal': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.1', 'min': '0'}),
            'corriente_nominal': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0'}),
            'eficiencia': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.1', 'min': '0', 'max': '100'}),
            'sistema_compatible': forms.Select(attrs={'class': 'form-select'}),
            'garantia_anos': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'largo_mm': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.1', 'min': '0'}),
            'ancho_mm': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.1', 'min': '0'}),
            'alto_mm': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.1', 'min': '0'}),
            'peso_kg': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.1', 'min': '0'}),
            'precio_proveedor': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0'}),
            'precio_venta': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0'}),
            'margen_porcentaje': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.1', 'min': '0', 'max': '100'}),
            'stock': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'imagen': forms.ClearableFileInput(attrs={'class': 'form-input', 'accept': 'image/*'}),
            'ficha_tecnica': forms.ClearableFileInput(attrs={'class': 'form-input', 'accept': '.pdf'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

    def clean_precio_venta(self):
        precio = self.cleaned_data.get('precio_venta')
        if precio is not None and precio <= 0:
            raise ValidationError('El precio de venta debe ser mayor a 0.')
        return precio

    def clean_stock(self):
        stock = self.cleaned_data.get('stock')
        if stock is not None and stock < 0:
            raise ValidationError('El stock no puede ser negativo.')
        return stock

    def clean(self):
        cleaned = super().clean()
        precio_proveedor = cleaned.get('precio_proveedor')
        precio_venta = cleaned.get('precio_venta')
        if precio_proveedor and precio_venta and precio_venta < precio_proveedor:
            self.add_error(
                'precio_venta',
                'El precio de venta no puede ser menor al precio del proveedor.',
            )
        return cleaned


class EquipoFilterForm(forms.Form):
    """Form for filtering equipment list."""

    categoria = forms.ChoiceField(
        choices=[('', 'Todas las categorías')] + list(Equipo.Categoria.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    fabricante = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Buscar fabricante...',
        }),
    )
    sistema = forms.ChoiceField(
        choices=[('', 'Todos los sistemas')] + list(Equipo.TipoSistemaCompatible.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    potencia_min = forms.FloatField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'Min W',
            'min': '0',
        }),
    )
    potencia_max = forms.FloatField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'Max W',
            'min': '0',
        }),
    )
    en_stock = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        label='Solo en stock',
    )
    buscar = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Buscar por nombre, modelo, SKU...',
        }),
    )


# ──────────────────────────────────────────────
# COTIZACIÓN FORMS
# ──────────────────────────────────────────────

class CotizacionForm(forms.ModelForm):
    """Form for creating/editing quotes."""

    class Meta:
        model = Cotizacion
        fields = [
            'proyecto', 'tipo_cliente', 'estado', 'fecha_emision',
            'usar_total_manual', 'total_manual',
            'descuento_porcentaje', 'iva_porcentaje',
            'costo_instalacion', 'costo_transporte',
            'dias_validez', 'condiciones',
        ]
        widgets = {
            'proyecto': forms.Select(attrs={'class': 'form-select'}),
            'tipo_cliente': forms.Select(attrs={'class': 'form-select'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'fecha_emision': forms.DateInput(attrs={
                'class': 'form-input', 'type': 'date',
            }, format='%Y-%m-%d'),
            'usar_total_manual': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-solar-600 border-gray-300 rounded focus:ring-solar-500',
                'id': 'id_usar_total_manual',
            }),
            'total_manual': forms.NumberInput(attrs={
                'class': 'form-input', 'step': '0.01', 'min': '0',
                'placeholder': 'Ingrese el total del proyecto',
                'id': 'id_total_manual',
            }),
            'descuento_porcentaje': forms.NumberInput(attrs={
                'class': 'form-input', 'step': '0.1', 'min': '0', 'max': '100',
            }),
            'iva_porcentaje': forms.NumberInput(attrs={
                'class': 'form-input', 'step': '0.1', 'value': '19',
            }),
            'costo_instalacion': forms.NumberInput(attrs={
                'class': 'form-input', 'step': '0.01', 'min': '0',
            }),
            'costo_transporte': forms.NumberInput(attrs={
                'class': 'form-input', 'step': '0.01', 'min': '0',
            }),
            'dias_validez': forms.NumberInput(attrs={
                'class': 'form-input', 'min': '1', 'value': '30',
            }),
            'condiciones': forms.Textarea(attrs={
                'class': 'form-input', 'rows': 4,
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('usar_total_manual'):
            total = cleaned_data.get('total_manual')
            if total is None or total <= 0:
                self.add_error(
                    'total_manual',
                    'Debes ingresar un valor total válido mayor a 0.',
                )
        return cleaned_data


class CotizacionItemForm(forms.ModelForm):
    """Form for adding items to a quote."""

    class Meta:
        model = CotizacionItem
        fields = ['equipo', 'cantidad', 'precio_unitario', 'descuento_item', 'aplica_iva']
        widgets = {
            'equipo': forms.Select(attrs={'class': 'form-select'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-input', 'min': '1', 'value': '1'}),
            'precio_unitario': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0'}),
            'descuento_item': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.1', 'min': '0', 'max': '100'}),
            'aplica_iva': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-solar-600 border-gray-300 rounded focus:ring-solar-500'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['precio_unitario'].required = False

    def clean_precio_unitario(self):
        value = self.cleaned_data.get('precio_unitario')
        if value is None:
            return Decimal('0')
        return value


CotizacionItemFormSet = forms.inlineformset_factory(
    Cotizacion,
    CotizacionItem,
    form=CotizacionItemForm,
    extra=1,
    can_delete=True,
)


# ──────────────────────────────────────────────
# CARGA FORMS
# ──────────────────────────────────────────────

class CargaForm(forms.ModelForm):
    """Form for adding/editing electrical loads."""

    class Meta:
        model = Carga
        fields = [
            'dispositivo', 'cantidad', 'potencia_nominal_w',
            'horas_uso_dia', 'factor_potencia', 'carga_reactiva',
            'factor_arranque', 'prioridad',
        ]
        widgets = {
            'dispositivo': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ej: Refrigerador, TV LED, Bomba de agua',
            }),
            'cantidad': forms.NumberInput(attrs={'class': 'form-input', 'min': '1', 'value': '1'}),
            'potencia_nominal_w': forms.NumberInput(attrs={
                'class': 'form-input', 'step': '0.1', 'min': '0', 'placeholder': 'Watts',
            }),
            'horas_uso_dia': forms.NumberInput(attrs={
                'class': 'form-input', 'step': '0.5', 'min': '0', 'max': '24',
            }),
            'factor_potencia': forms.NumberInput(attrs={
                'class': 'form-input', 'step': '0.01', 'min': '0', 'max': '1', 'value': '1.0',
            }),
            'carga_reactiva': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'factor_arranque': forms.NumberInput(attrs={
                'class': 'form-input', 'step': '0.1', 'min': '1', 'max': '10', 'value': '1.0',
            }),
            'prioridad': forms.Select(attrs={'class': 'form-select'}),
        }


CargaFormSet = forms.inlineformset_factory(
    Proyecto,
    Carga,
    form=CargaForm,
    extra=3,
    can_delete=True,
)


# ──────────────────────────────────────────────
# CARGA TIPO (LOAD CATALOG) FORMS
# ──────────────────────────────────────────────

class CargaTipoForm(forms.ModelForm):
    """Form for creating/editing electrical load types (catalog)."""

    class Meta:
        model = CargaTipo
        fields = [
            'nombre', 'categoria', 'potencia_nominal_w', 'horas_uso_dia',
            'factor_potencia', 'carga_reactiva', 'factor_arranque',
            'descripcion',
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ej: Refrigerador, TV LED 42", Bombillo LED 9W',
            }),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'potencia_nominal_w': forms.NumberInput(attrs={
                'class': 'form-input', 'step': '0.1', 'min': '0', 'placeholder': 'Watts',
            }),
            'horas_uso_dia': forms.NumberInput(attrs={
                'class': 'form-input', 'step': '0.5', 'min': '0', 'max': '24', 'placeholder': '8',
            }),
            'factor_potencia': forms.NumberInput(attrs={
                'class': 'form-input', 'step': '0.01', 'min': '0', 'max': '1', 'value': '1.0',
            }),
            'carga_reactiva': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'factor_arranque': forms.NumberInput(attrs={
                'class': 'form-input', 'step': '0.1', 'min': '1', 'max': '10', 'value': '1.0',
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-input', 'rows': 3, 'placeholder': 'Descripción o notas adicionales...',
            }),
            'activo': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo mostrar el campo 'activo' al editar (instance ya existe en BD)
        if self.instance and self.instance.pk:
            self.fields['activo'] = forms.BooleanField(
                required=False,
                widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
                label='Activo',
            )
