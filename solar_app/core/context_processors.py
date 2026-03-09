"""Context processors for the core app."""
from .models import CompanySettings


def company_settings(request):
    """Make company settings available in all templates."""
    try:
        settings_obj = CompanySettings.load()
    except Exception:
        settings_obj = None
    return {'company_settings': settings_obj}
