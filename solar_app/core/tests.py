"""
Core Django tests.
Backup and restore testing is now handled by APScheduler integration.
"""
from django.test import TestCase

from core.models import Cliente


class ClienteModelTestCase(TestCase):
    """Basic tests for Cliente model."""

    def test_cliente_model_exists(self):
        """Test that Cliente model is available."""
        self.assertTrue(hasattr(Cliente, 'objects'))
        self.assertTrue(callable(Cliente.objects.all))  # Queryset method exists
