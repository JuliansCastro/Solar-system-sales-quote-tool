#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'solar_app.settings')
os.chdir(project_dir)
django.setup()

from django.contrib.auth import get_user_model
from core.models import Cliente, Proyecto, Equipo, Departamento, Municipio

User = get_user_model()

try:
    # Step 1: Create admin user if doesn't exist
    admin_user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@test.com',
            'role': User.Role.ADMIN,
            'is_staff': True,
            'is_superuser': True,
        }
    )
    
    if created:
        admin_user.set_password('admin123')
        admin_user.save()
        print("✅ Admin user created")
    else:
        print("ℹ️ Admin user already exists")

    # Step 2: Get or find a valid Departamento and Municipio
    # Try to find Departamento for Bogota (should be "Cundinamarca" region typically)
    # or get the first available one
    try:
        departamento = Departamento.objects.filter(activo=True).first()
        if not departamento:
            print("⚠️ No active Departamento found")
            sys.exit(1)
        print(f"ℹ️ Using Departamento: {departamento.nombre}")
        
        municipio = Municipio.objects.filter(
            departamento=departamento, 
            activo=True
        ).first()
        if not municipio:
            print("⚠️ No active Municipio found")
            sys.exit(1)
        print(f"ℹ️ Using Municipio: {municipio.nombre}")
    except Exception as e:
        print(f"❌ Error finding location: {e}")
        sys.exit(1)

    # Step 3: Create test Cliente
    cliente, created = Cliente.objects.get_or_create(
        nombre='Cliente Test',
        defaults={
            'email': 'cliente@test.com',
            'telefono': '3001234567',
            'direccion': 'Calle 123 #456',
            'departamento': departamento,
            'municipio': municipio,
            'consumo_mensual_kwh': 500,
            'tarifa_electrica': 700,
            'estrato': 3,
            'creado_por': admin_user,
        }
    )
    if created:
        print("✅ Cliente created")
    else:
        print("ℹ️ Cliente already exists")

    # Step 4: Create test Proyecto
    proyecto, created = Proyecto.objects.get_or_create(
        codigo='TEST-2603-0001',
        defaults={
            'nombre': 'Proyecto Test',
            'cliente': cliente,
            'vendedor': admin_user,
            'tipo_sistema': Proyecto.TipoSistema.ON_GRID,
            'estado': Proyecto.Estado.EN_DISENO,
            'latitud': 4.711,
            'longitud': -74.0721,
            'direccion_instalacion': 'Calle 123 #456',
            'hsp_promedio': 4.5,
        }
    )
    if created:
        print("✅ Proyecto created")
    else:
        print("ℹ️ Proyecto already exists")

    # Step 5: Create test Equipment
    equipment_data = [
        {
            'nombre': 'Panel Solar 550W',
            'modelo': 'PS550W',
            'fabricante': 'SolarMax',
            'categoria': Equipo.Categoria.PANEL,
            'sku': 'PANEL-550-001',
            'potencia_nominal_w': 550,
            'voltaje_nominal': 48,
            'eficiencia': 22.5,
            'precio_venta': 250000,
        },
        {
            'nombre': 'Inversor On-Grid 5kW',
            'modelo': 'INV5K',
            'fabricante': 'Growatt',
            'categoria': Equipo.Categoria.INVERSOR,
            'sku': 'INVERSOR-5K-001',
            'potencia_nominal_w': 5000,
            'voltaje_nominal': 380,
            'eficiencia': 98.0,
            'precio_venta': 2500000,
        },
        {
            'nombre': 'Cable Solar 6mm',
            'modelo': 'CABLE6',
            'fabricante': 'ElectroMax',
            'categoria': Equipo.Categoria.CABLE,
            'sku': 'CABLE-6-001',
            'potencia_nominal_w': 0,
            'precio_venta': 15000,
        },
    ]

    for eq_data in equipment_data:
        equipo, created = Equipo.objects.get_or_create(
            sku=eq_data['sku'],
            defaults=eq_data
        )
        if created:
            print(f"✅ Equipo created: {eq_data['nombre']}")
        else:
            print(f"ℹ️ Equipo already exists: {eq_data['nombre']}")

    print("\n✓ Test data setup completed successfully!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
