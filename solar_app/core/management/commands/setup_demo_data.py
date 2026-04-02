from django.core.management.base import BaseCommand, CommandError

from core.services.demo_data_seed import seed_demo_data


class Command(BaseCommand):
    help = "Create demo admin, client, project, and baseline equipment catalog."

    def add_arguments(self, parser):
        parser.add_argument("--admin-username", default="admin")
        parser.add_argument("--admin-password", default="admin123")
        parser.add_argument("--admin-email", default="admin@test.com")

    def handle(self, *args, **options):
        try:
            summary = seed_demo_data(
                admin_username=options["admin_username"],
                admin_password=options["admin_password"],
                admin_email=options["admin_email"],
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                "Demo data ready "
                f"(admin_created={summary['admin_created']}, "
                f"cliente_created={summary['cliente_created']}, "
                f"proyecto_created={summary['proyecto_created']}, "
                f"equipment_created={summary['equipment']['created']}, "
                f"equipment_existing={summary['equipment']['existing']})."
            )
        )
