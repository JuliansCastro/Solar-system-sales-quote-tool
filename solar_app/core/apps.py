import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Solar Quote Core'

    def ready(self):
        import core.signals  # noqa: F401
        
        # Start backup scheduler in production environment
        from django.conf import settings
        
        if not settings.DEBUG:
            try:
                from core.backup_scheduler import start_scheduler
                start_scheduler()
            except Exception as e:
                logger.error(f"Failed to start backup scheduler: {e}", exc_info=True)
