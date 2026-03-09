"""
Quick smoke test for all main routes using Django's test client.
No need for a running server.
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'solar_app.settings')
django.setup()

from django.test import Client
from core.models import User

# Get or create admin
user = User.objects.filter(username='admin').first()
if not user:
    user = User.objects.create_superuser('admin', 'admin@solar.com', 'admin1234', role='admin')

client = Client()
logged_in = client.login(username='admin', password=sys.argv[1] if len(sys.argv) > 1 else 'admin1234')
print(f'Login: {"✅" if logged_in else "❌"}')
if not logged_in:
    print('Could not login. Aborting.')
    sys.exit(1)

pages = [
    ('/dashboard/',          200),
    ('/clientes/',           200),
    ('/clientes/nuevo/',     200),
    ('/proyectos/',          200),
    ('/proyectos/nuevo/',    200),
    ('/inventario/',         200),
    ('/inventario/nuevo/',   200),
    ('/cotizaciones/',       200),
    ('/cotizaciones/nueva/', 200),
    ('/accounts/users/',     200),
    ('/accounts/users/nuevo/', 200),
    ('/admin/',              200),
]

passed = 0
failed = 0
for path, expected in pages:
    try:
        r = client.get(path, follow=True)
        code = r.status_code
    except Exception as e:
        code = f'ERROR: {e}'

    ok = code == expected
    status = '✅' if ok else '❌'
    if ok:
        passed += 1
    else:
        failed += 1
    print(f'{status} {path} -> {code}')

print(f'\n{"="*40}')
print(f'Results: {passed} passed, {failed} failed out of {passed+failed} routes')
if failed == 0:
    print('🎉 All routes OK!')
else:
    print('⚠️  Some routes have issues.')
