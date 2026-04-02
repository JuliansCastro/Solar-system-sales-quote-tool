"""
Management command for controlling the backup scheduler.
"""
from django.core.management.base import BaseCommand

from core.ops.backup_scheduler import start_scheduler, stop_scheduler, get_scheduler_status


class Command(BaseCommand):
    help = "Manage the automatic database backup scheduler"

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            type=str,
            choices=['start', 'stop', 'status'],
            help='Action to perform: start, stop, or status',
        )

    def handle(self, *args, **options):
        action = options['action']

        if action == 'start':
            if start_scheduler():
                self.stdout.write(
                    self.style.SUCCESS('✓ Backup scheduler started successfully')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('✗ Failed to start backup scheduler')
                )

        elif action == 'stop':
            if stop_scheduler():
                self.stdout.write(
                    self.style.SUCCESS('✓ Backup scheduler stopped')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('✗ Failed to stop backup scheduler')
                )

        elif action == 'status':
            status = get_scheduler_status()
            self.stdout.write(f"\nBackup Scheduler Status")
            self.stdout.write("=" * 60)
            self.stdout.write(f"Running: {status['running']}\n")

            if status['jobs']:
                self.stdout.write("Scheduled Jobs:")
                self.stdout.write("-" * 60)
                for job in status['jobs']:
                    self.stdout.write(f"  • {job['name']}")
                    self.stdout.write(f"    ID: {job['id']}")
                    self.stdout.write(f"    Next Run: {job['next_run_time'] or 'Not scheduled'}")
                    self.stdout.write("")
            else:
                self.stdout.write("No jobs scheduled")
