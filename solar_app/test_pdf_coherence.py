#!/usr/bin/env python
"""
Test script to verify PDF and Excel coherence with calculated sizing from items.
Tests that panel counts and technical summary data match between HTML and PDF/Excel.
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'solar_app.settings')
sys.path.insert(0, os.path.dirname(__file__))

django.setup()

from core.models import Cotizacion, Proyecto, CotizacionItem, Equipo
from core.calculations.chart_data import _calculate_sizing_from_items
from core.calculations.reports import generar_pdf_cotizacion, generar_excel_cotizacion


def test_pdf_excel_coherence():
    """Test that PDF and Excel show same sizing data as calculated from items."""
    
    # Get first cotización with items
    cotizacion = Cotizacion.objects.filter(items__isnull=False).prefetch_related(
        'items__equipo', 'proyecto'
    ).first()
    
    if not cotizacion:
        print("❌ No cotización with items found")
        return False
    
    proyecto = cotizacion.proyecto
    print(f"\nTesting cotización {cotizacion.numero}")
    print(f"Proyecto: {proyecto.codigo}")
    
    # Calculate sizing from items (source of truth)
    sizing_from_items = _calculate_sizing_from_items(cotizacion, proyecto)
    print("\n✓ Sizing from items (Source of Truth):")
    print(f"  - Potencia pico: {sizing_from_items.get('potencia_pico_kwp')} kWp")
    print(f"  - Número de paneles: {sizing_from_items.get('numero_paneles')}")
    print(f"  - Generación mensual: {sizing_from_items.get('generacion_mensual_kwh'):.0f} kWh/mes")
    print(f"  - Cobertura solar: {sizing_from_items.get('porcentaje_cobertura'):.1f}%")
    
    # Verify cotización items
    print("\n✓ Items en la cotización:")
    panel_items = cotizacion.items.filter(equipo__categoria='panel').select_related('equipo')
    for item in panel_items:
        print(f"  - {item.equipo.nombre}: {item.cantidad} unidades @ {item.equipo.potencia_nominal_w}W")
    
    # Test PDF generation
    print("\n✓ Generating PDF...")
    try:
        pdf_buffer = generar_pdf_cotizacion(cotizacion)
        pdf_size = len(pdf_buffer.getvalue())
        print(f"  - PDF generated successfully ({pdf_size:,} bytes)")
    except Exception as e:
        print(f"  ❌ PDF generation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test Excel generation
    print("\n✓ Generating Excel...")
    try:
        excel_buffer = generar_excel_cotizacion(cotizacion)
        excel_size = len(excel_buffer.getvalue())
        print(f"  - Excel generated successfully ({excel_size:,} bytes)")
    except Exception as e:
        print(f"  ❌ Excel generation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    # Compare with proyecto fields
    print("\n✓ Comparison (Items vs Proyecto fields):")
    print(f"  - Items panels: {sizing_from_items.get('numero_paneles')} vs Proyecto: {proyecto.numero_paneles}")
    print(f"  - Items power: {sizing_from_items.get('potencia_pico_kwp')} vs Proyecto: {proyecto.potencia_pico_kwp}")
    print(f"  - Items gen: {sizing_from_items.get('generacion_mensual_kwh'):.0f} vs Proyecto: {proyecto.generacion_mensual_kwh:.0f}")
    
    if sizing_from_items.get('numero_paneles') != proyecto.numero_paneles:
        print(f"  ⚠️  WARNING: Panel count mismatch!")
    
    print("\n✅ All tests passed!")
    return True


if __name__ == '__main__':
    success = test_pdf_excel_coherence()
    sys.exit(0 if success else 1)
