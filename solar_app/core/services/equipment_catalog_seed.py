from __future__ import annotations

from typing import Any

from core.models import Equipo

DEFAULT_EQUIPMENT_CATALOG: list[dict[str, Any]] = [
    {
        "nombre": "Inversor Solar Hibrido 24V 2kW",
        "modelo": "HYBRID-2K-24V",
        "fabricante": "SolarMax",
        "categoria": Equipo.Categoria.INVERSOR,
        "sku": "INV-HYBRID-2K-24V-001",
        "potencia_nominal_w": 2000,
        "voltaje_nominal": 24,
        "eficiencia": 96.5,
        "precio_venta": 3500000,
        "precio_proveedor": 2000000,
        "descripcion": "Inversor solar hibrido de 24V, 2kW monofasico de bajo voltaje MPPT, sinusoidal pura",
    },
    {
        "nombre": "Bateria Litio 24V 100Ah 3.36kWh",
        "modelo": "LIION-24V-100AH",
        "fabricante": "BlueSolar",
        "categoria": Equipo.Categoria.BATERIA,
        "sku": "BAT-LIION-24V-100-001",
        "potencia_nominal_w": 3360,
        "voltaje_nominal": 24,
        "eficiencia": 98.0,
        "precio_venta": 8500000,
        "precio_proveedor": 5000000,
        "descripcion": "Bateria Litio con BMS 24V / 100Ah de 3.36Kwh, 6000 ciclos y 90% DOD",
    },
    {
        "nombre": "Panel Solar 450W",
        "modelo": "PANEL-450W",
        "fabricante": "SolarPanel Pro",
        "categoria": Equipo.Categoria.PANEL,
        "sku": "PANEL-450W-001",
        "potencia_nominal_w": 450,
        "voltaje_nominal": 49.28,
        "corriente_nominal": 11.57,
        "eficiencia": 22.5,
        "precio_venta": 450000,
        "precio_proveedor": 250000,
        "descripcion": "Panel solar 450W - 49.28Voc, 11.57Isc",
    },
    {
        "nombre": "Breaker DC 2 Polos 25A",
        "modelo": "BREAKER-DC-25A",
        "fabricante": "Schneider",
        "categoria": Equipo.Categoria.PROTECCION,
        "sku": "BREAKER-DC-550V-25A-001",
        "potencia_nominal_w": 0,
        "precio_venta": 150000,
        "precio_proveedor": 80000,
        "descripcion": "Proteccion breaker DC 2 Polos DC550V 2P 25A",
    },
    {
        "nombre": "DPS Descargador Sobretension",
        "modelo": "DPS-DC-600V",
        "fabricante": "Phoenix",
        "categoria": Equipo.Categoria.PROTECCION,
        "sku": "DPS-DC-600V-20KA-001",
        "potencia_nominal_w": 0,
        "precio_venta": 200000,
        "precio_proveedor": 100000,
        "descripcion": "Proteccion solar DPS - Descargador DC600V",
    },
    {
        "nombre": "Cable Solar 6mm2 Rojo",
        "modelo": "CABLE-6MM-RED",
        "fabricante": "ElectroMax",
        "categoria": Equipo.Categoria.CABLE,
        "sku": "CABLE-6MM-RED-001",
        "potencia_nominal_w": 0,
        "precio_venta": 5000,
        "precio_proveedor": 2000,
        "descripcion": "Cable solar 6mm2 rojo x metro",
    },
    {
        "nombre": "Cable Solar 6mm2 Negro",
        "modelo": "CABLE-6MM-BLACK",
        "fabricante": "ElectroMax",
        "categoria": Equipo.Categoria.CABLE,
        "sku": "CABLE-6MM-BLACK-001",
        "potencia_nominal_w": 0,
        "precio_venta": 5000,
        "precio_proveedor": 2000,
        "descripcion": "Cable solar 6mm2 negro x metro",
    },
    {
        "nombre": "Conector MC4 Panel Solar",
        "modelo": "MC4-CONNECTOR",
        "fabricante": "Phoenix Contact",
        "categoria": Equipo.Categoria.ACCESORIO,
        "sku": "MC4-CONNECTOR-001",
        "potencia_nominal_w": 0,
        "precio_venta": 8000,
        "precio_proveedor": 4000,
        "descripcion": "Conector MC4 para panel solar",
    },
    {
        "nombre": "Estructura Anclaje L-Foot 105mm",
        "modelo": "L-FOOT-105MM",
        "fabricante": "SolarRack",
        "categoria": Equipo.Categoria.ESTRUCTURA,
        "sku": "LFOOT-105MM-001",
        "potencia_nominal_w": 0,
        "precio_venta": 25000,
        "precio_proveedor": 12000,
        "descripcion": "Estructura anclaje L-Foot (105mm)",
    },
    {
        "nombre": "Varilla Puesta A Tierra 2.4M 5/8",
        "modelo": "GROUND-ROD-2.4M",
        "fabricante": "ElectroMax",
        "categoria": Equipo.Categoria.ESTRUCTURA,
        "sku": "GROUNDROD-2.4M-001",
        "potencia_nominal_w": 0,
        "precio_venta": 35000,
        "precio_proveedor": 18000,
        "descripcion": "Varilla puesta a tierra 2.40M x 5/8 con grapa",
    },
    {
        "nombre": "Riel Estructura Aluminio 4.2m",
        "modelo": "RAIL-ALU-4.2M",
        "fabricante": "SolarRack",
        "categoria": Equipo.Categoria.ESTRUCTURA,
        "sku": "RAIL-ALU-4.2M-001",
        "potencia_nominal_w": 0,
        "precio_venta": 120000,
        "precio_proveedor": 60000,
        "descripcion": "Riel estructura en aluminio 4.2m",
    },
    {
        "nombre": "Caja Protecciones Sistema Solar",
        "modelo": "PROTECTION-BOX",
        "fabricante": "ElectroMax",
        "categoria": Equipo.Categoria.PROTECCION,
        "sku": "PROTBOX-SOLAR-001",
        "potencia_nominal_w": 0,
        "precio_venta": 180000,
        "precio_proveedor": 90000,
        "descripcion": "Caja protecciones",
    },
]


def seed_equipment_catalog(
    *, default_stock: int = 50, mark_active: bool = True
) -> dict[str, int]:
    created = 0
    existing = 0

    for equipment in DEFAULT_EQUIPMENT_CATALOG:
        _, was_created = Equipo.objects.get_or_create(
            sku=equipment["sku"],
            defaults={
                **equipment,
                "stock": default_stock,
                "activo": mark_active,
            },
        )
        if was_created:
            created += 1
        else:
            existing += 1

    return {
        "created": created,
        "existing": existing,
        "total": Equipo.objects.count(),
    }
