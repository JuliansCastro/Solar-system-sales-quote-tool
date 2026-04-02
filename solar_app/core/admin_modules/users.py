"""User admin configuration."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from core.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "role", "is_active")
    list_filter = ("role", "is_active", "is_staff")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Información adicional", {"fields": ("role", "phone", "company")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Información adicional", {"fields": ("role", "phone", "company")}),
    )
