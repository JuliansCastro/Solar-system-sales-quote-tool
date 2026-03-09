"""
WSGI config for solar_app project.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'solar_app.settings')
application = get_wsgi_application()
