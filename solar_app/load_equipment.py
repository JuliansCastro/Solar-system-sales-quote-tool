# -*- coding: utf-8 -*-
from django.contrib.auth import get_user_model
from core.models import Equipo

User = get_user_model()

equipos_data = [
    {'nombre': 'Inversor Solar Hibrido 24V 2kW', 'modelo': 'HYBRID-2K-24V', 'fabricante': 'SolarMax', 'categoria': 'inversor', 'sku': 'INV-HYBRID-2K-24V-001', 'potencia_nominal_w': 2000, 'voltaje_nominal': 24, 'eficiencia': 96.5, 'precio_venta': 3500000, 'precio_proveedor': 2000000},
    {'nombre': 'Bateria Litio 24V 100Ah', 'modelo': 'LIION-24V-100AH', 'fabricante': 'BlueSolar', 'categoria': 'bateria', 'sku': 'BAT-LIION-24V-100-001', 'potencia_nominal_w': 3360, 'voltaje_nominal': 24, 'eficiencia': 98.0, 'precio_venta': 8500000, 'precio_proveedor': 5000000},
    {'nombre': 'Panel Solar 450W', 'modelo': 'PANEL-450W', 'fabricante': 'SolarPanel Pro', 'categoria': 'panel', 'sku': 'PANEL-450W-001', 'potencia_nominal_w': 450, 'voltaje_nominal': 49.28, 'corriente_nominal': 11.57, 'eficiencia': 22.5, 'precio_venta': 450000, 'precio_proveedor': 250000},
    {'nombre': 'Breaker DC 2 Polos 25A', 'modelo': 'BREAKER-DC-25A', 'fabricante': 'Schneider', 'categoria': 'proteccion', 'sku': 'BREAKER-DC-550V-25A-001', 'potencia_nominal_w': 0, 'precio_venta': 150000, 'precio_proveedor': 80000},
    {'nombre': 'DPS Descargador Sobretension', 'modelo': 'DPS-DC-600V', 'fabricante': 'Phoenix', 'categoria': 'proteccion', 'sku': 'DPS-DC-600V-20KA-001', 'potencia_nominal_w': 0, 'precio_venta': 200000, 'precio_proveedor': 100000},
    {'nombre': 'Cable Solar 6mm2 Rojo', 'modelo': 'CABLE-6MM-RED', 'fabricante': 'ElectroMax', 'categoria': 'cable', 'sku': 'CABLE-6MM-RED-001', 'potencia_nominal_w': 0, 'precio_venta': 5000, 'precio_proveedor': 2000},
    {'nombre': 'Cable Solar 6mm2 Negro', 'modelo': 'CABLE-6MM-BLACK', 'fabricante': 'ElectroMax', 'categoria': 'cable', 'sku': 'CABLE-6MM-BLACK-001', 'potencia_nominal_w': 0, 'precio_venta': 5000, 'precio_proveedor': 2000},
    {'nombre': 'Conector MC4 Panel Solar', 'modelo': 'MC4-CONNECTOR', 'fabricante': 'Phoenix Contact', 'categoria': 'accesorio', 'sku': 'MC4-CONNECTOR-001', 'potencia_nominal_w': 0, 'precio_venta': 8000, 'precio_proveedor': 4000},
    {'nombre': 'Estructura Anclaje L-Foot 105mm', 'modelo': 'L-FOOT-105MM', 'fabricante': 'SolarRack', 'categoria': 'estructura', 'sku': 'LFOOT-105MM-001', 'potencia_nominal_w': 0, 'precio_venta': 25000, 'precio_proveedor': 12000},
    {'nombre': 'Varilla Puesta A Tierra 2.4M', 'modelo': 'GROUND-ROD-2.4M', 'fabricante': 'ElectroMax', 'categoria': 'estructura', 'sku': 'GROUNDROD-2.4M-001', 'potencia_nominal_w': 0, 'precio_venta': 35000, 'precio_proveedor': 18000},
    {'nombre': 'Riel Estructura Aluminio 4.2m', 'modelo': 'RAIL-ALU-4.2M', 'fabricante': 'SolarRack', 'categoria': 'estructura', 'sku': 'RAIL-ALU-4.2M-001', 'potencia_nominal_w': 0, 'precio_venta': 120000, 'precio_proveedor': 60000},
    {'nombre': 'Caja Protecciones Sistema Solar', 'modelo': 'PROTECTION-BOX', 'fabricante': 'ElectroMax', 'categoria': 'proteccion', 'sku': 'PROTBOX-SOLAR-001', 'potencia_nominal_w': 0, 'precio_venta': 180000, 'precio_proveedor': 90000},
]

print("Agregando equipos al sistema...")
for eq_data in equipos_data:
    equipo, created = Equipo.objects.get_or_create(
        sku=eq_data['sku'],
        defaults={**eq_data, 'stock': 50, 'activo': True}
    )
    if created:
        print(f"OK {eq_data['nombre']}")
    else:
        print(f"EXISTS {eq_data['nombre']}")

print(f"TOTAL: {Equipo.objects.count()}")
