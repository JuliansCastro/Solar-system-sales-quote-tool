from django.core.management.base import BaseCommand

from core.services.equipment_catalog_seed import seed_equipment_catalog


class Command(BaseCommand):
    help = "Load the default equipment catalog in an idempotent way."

    def add_arguments(self, parser):
        parser.add_argument(
            "--stock",
            type=int,
            default=50,
            help="Default stock to assign when creating equipment.",
        )
        parser.add_argument(
            "--inactive",
            action="store_true",
            help="Create new records with activo=False.",
        )

    def handle(self, *args, **options):
        summary = seed_equipment_catalog(
            default_stock=options["stock"],
            mark_active=not options["inactive"],
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Equipment catalog loaded "
                f"(created={summary['created']}, existing={summary['existing']}, total={summary['total']})."
            )
        )
