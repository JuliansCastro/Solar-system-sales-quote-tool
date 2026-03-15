from django.contrib.auth import get_user_model
from core.models import Equipo

User = get_user_model()

# Equipment list with proper categorization and pricing
equipos_data = [
    {
        'nombre': 'Inversor Solar Híbrido 24V 2kW',
        'modelo': 'HYBRID-2K-24V',
        'fabricante': 'SolarMax',
        'categoria': 'inversor',
        'sku': 'INV-HYBRID-2K-24V-001',
        'potencia_nominal_w': 2000,
        'voltaje_nominal': 24,
        'eficiencia': 96.5,
        'precio_venta': 3500000,
        'precio_proveedor': 2000000,
        'descripcion': 'Inversor solar híbrido de 24V, 2kW monofásico de bajo voltaje MPPT, sinusoidal pura'
    },
    {
        'nombre': 'Batería Litio 24V 100Ah 3.36kWh',
        'modelo': 'LIION-24V-100AH',
        'fabricante': 'BlueSolar',
        'categoria': 'bateria',
        'sku': 'BAT-LIION-24V-100-001',
        'potencia_nominal_w': 3360,
        'voltaje_nominal': 24,
        'eficiencia': 98.0,
        'precio_venta': 8500000,
        'precio_proveedor': 5000000,
        'descripcion': 'Batería Litio con BMS 24V / 100Ah de 3.36Kwh, 6000ciclos y 90%DOD'
    },
    {
        'nombre': 'Panel Solar 450W',
        'modelo': 'PANEL-450W',
        'fabricante': 'SolarPanel Pro',
        'categoria': 'panel',
        'sku': 'PANEL-450W-001',
        'potencia_nominal_w': 450,
        'voltaje_nominal': 49.28,
        'corriente_nominal': 11.57,
        'eficiencia': 22.5,
        'precio_venta': 450000,
        'precio_proveedor': 250000,
        'descripcion': 'Panel solar 450W - 49.28voc, 11.57Isc'
    },
    {
        'nombre': 'Breaker DC 2 Polos 25A',
        'modelo': 'BREAKER-DC-25A',
        'fabricante': 'Schneider',
        'categoria': 'proteccion',
        'sku': 'BREAKER-DC-550V-25A-001',
        'potencia_nominal_w': 0,
        'precio_venta': 150000,
        'precio_proveedor': 80000,
        'descripcion': 'Proteccion breaker DC 2 Polos DC550V 2P 25A'
    },
    {
        'nombre': 'DPS Descargador Sobretension',
        'modelo': 'DPS-DC-600V',
        'fabricante': 'Phoenix',
        'categoria': 'proteccion',
        'sku': 'DPS-DC-600V-20KA-001',
        'potencia_nominal_w': 0,
        'precio_venta': 200000,
        'precio_proveedor': 100000,
        'descripcion': 'Proteccion solar DPS - Descargador DC600V'
    },
    {
        'nombre': 'Cable Solar 6mm2 Rojo',
        'modelo': 'CABLE-6MM-RED',
        'fabricante': 'ElectroMax',
        'categoria': 'cable',
        'sku': 'CABLE-6MM-RED-001',
        'potencia_nominal_w': 0,
        'precio_venta': 5000,
        'precio_proveedor': 2000,
        'descripcion': 'Cable solar 6mm2 Rojo x metro'
    },
    {
        'nombre': 'Cable Solar 6mm2 Negro',
        'modelo': 'CABLE-6MM-BLACK',
        'fabricante': 'ElectroMax',
        'categoria': 'cable',
        'sku': 'CABLE-6MM-BLACK-001',
        'potencia_nominal_w': 0,
        'precio_venta': 5000,
        'precio_proveedor': 2000,
        'descripcion': 'Cable solar 6mm2 Negro x metro'
    },
    {
        'nombre': 'Conector MC4 Panel Solar',
        'modelo': 'MC4-CONNECTOR',
        'fabricante': 'Phoenix Contact',
        'categoria': 'accesorio',
        'sku': 'MC4-CONNECTOR-001',
        'potencia_nominal_w': 0,
        'precio_venta': 8000,
        'precio_proveedor': 4000,
        'descripcion': 'Conector MC4 para panel solar'
    },
    {
        'nombre': 'Estructura Anclaje L-Foot 105mm',
        'modelo': 'L-FOOT-105MM',
        'fabricante': 'SolarRack',
        'categoria': 'estructura',
        'sku': 'LFOOT-105MM-001',
        'potencia_nominal_w': 0,
        'precio_venta': 25000,
        'precio_proveedor': 12000,
        'descripcion': 'Estructura anclaje L-Foot (105mm)'
    },
    {
        'nombre': 'Varilla Puesta A Tierra 2.4M 5/8',
        'modelo': 'GROUND-ROD-2.4M',
        'fabricante': 'ElectroMax',
        'categoria': 'estructura',
        'sku': 'GROUNDROD-2.4M-001',
        'potencia_nominal_w': 0,
        'precio_venta': 35000,
        'precio_proveedor': 18000,
        'descripcion': 'Varilla Puesta A Tierra 2.40M X 5/8 Con Grapa'
    },
    {
        'nombre': 'Riel Estructura Aluminio 4.2m',
        'modelo': 'RAIL-ALU-4.2M',
        'fabricante': 'SolarRack',
        'categoria': 'estructura',
        'sku': 'RAIL-ALU-4.2M-001',
        'potencia_nominal_w': 0,
        'precio_venta': 120000,
        'precio_proveedor': 60000,
        'descripcion': 'Riel estructura en aluminio 4,2m'
    },
    {
        'nombre': 'Caja Protecciones Sistema Solar',
        'modelo': 'PROTECTION-BOX',
        'fabricante': 'ElectroMax',
        'categoria': 'proteccion',
        'sku': 'PROTBOX-SOLAR-001',
        'potencia_nominal_w': 0,
        'precio_venta': 180000,
        'precio_proveedor': 90000,
        'descripcion': 'Caja protecciones'
    },
]

print("Agregando equipos al sistema...")
for eq_data in equipos_data:
    equipo, created = Equipo.objects.get_or_create(
        sku=eq_data['sku'],
        defaults={**eq_data, 'stock': 50, 'activo': True}
    )
    if created:
        print(f"✅ {eq_data['nombre']}")
    else:
        print(f"ℹ️  {eq_data['nombre']} ya existe")

print(f"\n✓ Total equipos en sistema: {Equipo.objects.count()}")
