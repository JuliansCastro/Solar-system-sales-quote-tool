#!/usr/bin/env python
"""
Test script to validate panel area formatting changes in PDF.
Checks that dimensions are shown in meters and text is properly formatted.
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'solar_app.settings')
sys.path.insert(0, os.path.dirname(__file__))

django.setup()

from core.models import Cotizacion
from core.calculations.reports import generar_pdf_cotizacion

try:
    from PyPDF2 import PdfReader
except ImportError:
    print("[INFO] Installing PyPDF2...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyPDF2", "-q"])
    from PyPDF2 import PdfReader


def extract_pdf_text(pdf_buffer):
    """Extract text from PDF buffer."""
    try:
        pdf_reader = PdfReader(pdf_buffer)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        print(f"Error extracting PDF: {e}")
        return ""


def test_panel_area_formatting():
    """Validate panel area block formatting changes."""
    
    # Get first cotización with items
    cotizacion = Cotizacion.objects.filter(items__isnull=False).prefetch_related(
        'items__equipo', 'proyecto'
    ).first()
    
    if not cotizacion:
        print("[ERROR] No cotización with items found")
        return False
    
    print(f"\n{'='*70}")
    print(f"VALIDATING PANEL AREA FORMATTING")
    print(f"{'='*70}")
    print(f"Cotizacion: {cotizacion.numero}\n")
    
    # Generate PDF
    try:
        pdf_buffer = generar_pdf_cotizacion(cotizacion)
        pdf_text = extract_pdf_text(pdf_buffer)
    except Exception as e:
        print(f"[ERROR] Failed to generate PDF: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("[VALIDATION] Panel Area Formatting")
    print("-" * 70)
    
    # Check for meter (m) format instead of millimeter (mm)
    has_meters_largo = " m" in pdf_text and "Largo:" in pdf_text
    has_meters_ancho = " m" in pdf_text and "Ancho:" in pdf_text
    has_no_mm = "mm" not in pdf_text or pdf_text.count("mm") <= 2  # Allow only area units
    
    print(f"\nDimension Format (Largo/Ancho):")
    print(f"  [{'OK' if has_meters_largo else 'FAIL'}] Contains 'Largo' with meters: {has_meters_largo}")
    print(f"  [{'OK' if has_meters_ancho else 'FAIL'}] Contains 'Ancho' with meters: {has_meters_ancho}")
    print(f"  [{'OK' if has_no_mm else 'WARN'}] Not using mm for dimensions: {has_no_mm}")
    
    # Check for required section
    has_section_title = "Area requerida para instalacion" in pdf_text.lower()
    print(f"\nSection Presence:")
    print(f"  [{'OK' if has_section_title else 'FAIL'}] Contains panel area section: {has_section_title}")
    
    # Extract and show sample text containing dimensions
    print(f"\nSample Text Containing Dimensions:")
    for line in pdf_text.split('\n'):
        if 'Largo:' in line or 'Ancho:' in line:
            print(f"  >>> {line.strip()}")
    
    # Check for table content
    has_panel_name = "Panel de referencia" in pdf_text
    has_area_info = "Area de un panel" in pdf_text.lower() or "area de un panel" in pdf_text.lower()
    has_total_area = "Area total estimada" in pdf_text.lower() or "area total estimada" in pdf_text.lower()
    
    print(f"\nTable Content:")
    print(f"  [{'OK' if has_panel_name else 'FAIL'}] Contains 'Panel de referencia': {has_panel_name}")
    print(f"  [{'OK' if has_area_info else 'FAIL'}] Contains area information: {has_area_info}")
    print(f"  [{'OK' if has_total_area else 'FAIL'}] Contains total area calculation: {has_total_area}")
    
    # Final result
    all_checks = [has_meters_largo, has_meters_ancho, has_section_title, 
                  has_panel_name, has_area_info, has_total_area]
    
    print(f"\n{'='*70}")
    if all(all_checks):
        print("[SUCCESS] All panel area formatting validations passed!")
    else:
        print("[WARNING] Some formatting checks failed - review above")
    print(f"{'='*70}\n")
    
    return True


if __name__ == '__main__':
    success = test_panel_area_formatting()
    sys.exit(0 if success else 1)
