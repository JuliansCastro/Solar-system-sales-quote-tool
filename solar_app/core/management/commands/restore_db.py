import gzip
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connections


class Command(BaseCommand):
    help = "Restore database from a backup file created by backup_db."

    def add_arguments(self, parser):
        parser.add_argument(
            "backup_file",
            help="Path to backup file (.sqlite3.gz or .sql.gz).",
        )
        parser.add_argument(
            "--yes-i-know",
            action="store_true",
            help="Required confirmation flag because restore is destructive.",
        )

    def handle(self, *args, **options):
        if not options["yes_i_know"]:
            raise CommandError(
                "This operation is destructive. Re-run with --yes-i-know after validating your backup path."
            )

        backup_file = Path(options["backup_file"]).expanduser().resolve()
        if not backup_file.exists():
            raise CommandError(f"Backup file not found: {backup_file}")

        engine = settings.DATABASES["default"]["ENGINE"]
        if engine == "django.db.backends.sqlite3":
            self._restore_sqlite(backup_file)
        elif engine == "django.db.backends.postgresql":
            self._restore_postgres(backup_file)
        else:
            raise CommandError(f"Unsupported database engine for restore: {engine}")

        self.stdout.write(self.style.SUCCESS(f"Database restored from: {backup_file}"))

    def _restore_sqlite(self, backup_file: Path) -> None:
        db_name = settings.DATABASES["default"].get("NAME")
        if not db_name:
            raise CommandError("SQLite database path is not configured.")

        target_file = Path(db_name)
        target_file.parent.mkdir(parents=True, exist_ok=True)

        # Close Django DB connection before replacing the SQLite file.
        connections["default"].close()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".sqlite3") as tmp_file:
            tmp_path = Path(tmp_file.name)

        try:
            with gzip.open(backup_file, "rb") as src, tmp_path.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            os.replace(tmp_path, target_file)
        finally:
            tmp_path.unlink(missing_ok=True)

    def _restore_postgres(self, backup_file: Path) -> None:
        db = settings.DATABASES["default"]
        db_name = db.get("NAME")
        db_user = db.get("USER")
        db_host = db.get("HOST") or "localhost"
        db_port = str(db.get("PORT") or "5432")
        db_password = db.get("PASSWORD")

        if not db_name or not db_user:
            raise CommandError("PostgreSQL NAME and USER are required for restore.")

        env = os.environ.copy()
        if db_password:
            env["PGPASSWORD"] = db_password

        command = [
            "psql",
            "-v",
            "ON_ERROR_STOP=1",
            "-h",
            db_host,
            "-p",
            db_port,
            "-U",
            db_user,
            "-d",
            db_name,
        ]

        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
        except FileNotFoundError as exc:
            raise CommandError("psql is not installed or is not available in PATH.") from exc

        if process.stdin is None:
            process.kill()
            raise CommandError("Could not open stdin for psql restore process.")

        try:
            with gzip.open(backup_file, "rb") as src:
                shutil.copyfileobj(src, process.stdin)
        except OSError as exc:
            process.kill()
            raise CommandError(f"Failed to read backup file {backup_file}: {exc}") from exc
        finally:
            process.stdin.close()

        stdout_bytes, stderr_bytes = process.communicate()
        if process.returncode != 0:
            raise CommandError(
                "psql restore failed with code "
                f"{process.returncode}: {stderr_bytes.decode('utf-8', errors='replace')}"
            )

        if stdout_bytes:
            self.stdout.write(stdout_bytes.decode("utf-8", errors="replace"))
