"""Quick smoke test for all main routes using Django's test client."""

import os
import sys

import django


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'solar_app.settings')
    django.setup()

    from django.test import Client
    from core.models import User

    user = User.objects.filter(username='admin').first()
    if not user:
        user = User.objects.create_superuser(
            'admin',
            'admin@solar.com',
            'admin1234',
            role='admin',
        )

    client = Client()
    logged_in = client.login(
        username='admin',
        password=sys.argv[1] if len(sys.argv) > 1 else 'admin1234',
    )
    print(f'Login: {"OK" if logged_in else "FAIL"}')
    if not logged_in:
        print('Could not login. Aborting.')
        sys.exit(1)

    pages = [
        ('/dashboard/', 200),
        ('/clientes/', 200),
        ('/clientes/nuevo/', 200),
        ('/proyectos/', 200),
        ('/proyectos/nuevo/', 200),
        ('/inventario/', 200),
        ('/inventario/nuevo/', 200),
        ('/cotizaciones/', 200),
        ('/cotizaciones/nueva/', 200),
        ('/accounts/users/', 200),
        ('/accounts/users/nuevo/', 200),
        ('/admin/', 200),
    ]

    passed = 0
    failed = 0
    for path, expected in pages:
        try:
            response = client.get(path, follow=True)
            code = response.status_code
        except Exception as exc:  # pragma: no cover
            code = f'ERROR: {exc}'

        ok = code == expected
        status = 'OK' if ok else 'FAIL'
        if ok:
            passed += 1
        else:
            failed += 1
        print(f'{status} {path} -> {code}')

    print(f'\n{"="*40}')
    print(f'Results: {passed} passed, {failed} failed out of {passed + failed} routes')
    if failed == 0:
        print('All routes OK!')
    else:
        print('Some routes have issues.')


if __name__ == '__main__':
    main()
