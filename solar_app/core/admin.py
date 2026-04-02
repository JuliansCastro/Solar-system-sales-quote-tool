"""Admin entrypoint.

Keeping this module as Django's discovery entrypoint while admin registrations
are organized in domain-specific modules.
"""

from .admin_modules import *  # noqa: F403,F401
