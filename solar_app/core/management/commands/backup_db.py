import gzip
import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create a database backup with checksum and metadata."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            default=os.getenv("BACKUP_DIR", str(settings.BASE_DIR / "backups")),
            help="Directory where backups will be written.",
        )
        parser.add_argument(
            "--label",
            default="manual",
            help="Short label to identify the backup origin (manual, hourly, before-deploy, etc.).",
        )
        parser.add_argument(
            "--retention-hours",
            type=int,
            default=int(os.getenv("BACKUP_RETENTION_HOURS", "168")),
            help="Delete .gz backups older than this amount of hours.",
        )
        parser.add_argument(
            "--skip-purge",
            action="store_true",
            help="Do not delete old backups after creating the new backup.",
        )

    def handle(self, *args, **options):
        output_dir = Path(options["output_dir"]).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        label = self._sanitize_label(options["label"])
        now = datetime.now(timezone.utc)
        timestamp = now.strftime("%Y%m%d_%H%M%S")

        engine = settings.DATABASES["default"]["ENGINE"]
        if engine == "django.db.backends.sqlite3":
            backup_file = output_dir / f"{timestamp}_sqlite3_{label}.sqlite3.gz"
            self._backup_sqlite(backup_file)
        elif engine == "django.db.backends.postgresql":
            backup_file = output_dir / f"{timestamp}_postgres_{label}.sql.gz"
            self._backup_postgres(backup_file)
        else:
            raise CommandError(f"Unsupported database engine for backup: {engine}")

        checksum = self._write_sha256(backup_file)
        self._write_metadata(backup_file, checksum, engine, now, label)

        if not options["skip_purge"]:
            removed = self._purge_old_backups(
                output_dir=output_dir,
                retention_hours=options["retention_hours"],
            )
            self.stdout.write(self.style.WARNING(f"Removed old backups: {removed}"))

        self.stdout.write(self.style.SUCCESS(f"Backup created: {backup_file}"))

    def _backup_sqlite(self, backup_file: Path) -> None:
        db_name = settings.DATABASES["default"].get("NAME")
        if not db_name:
            raise CommandError("SQLite database path is not configured.")

        source_file = Path(db_name)
        if not source_file.exists():
            raise CommandError(f"SQLite database file does not exist: {source_file}")

        with source_file.open("rb") as src, gzip.open(backup_file, "wb") as dst:
            shutil.copyfileobj(src, dst)

    def _backup_postgres(self, backup_file: Path) -> None:
        db = settings.DATABASES["default"]
        db_name = db.get("NAME")
        db_user = db.get("USER")
        db_host = db.get("HOST") or "localhost"
        db_port = str(db.get("PORT") or "5432")
        db_password = db.get("PASSWORD")

        if not db_name or not db_user:
            raise CommandError("PostgreSQL NAME and USER are required for backup.")

        env = os.environ.copy()
        if db_password:
            env["PGPASSWORD"] = db_password

        command = [
            "pg_dump",
            "--no-owner",
            "--no-privileges",
            "--clean",
            "--if-exists",
            "-h",
            db_host,
            "-p",
            db_port,
            "-U",
            db_user,
            db_name,
        ]

        try:
            with gzip.open(backup_file, "wb") as compressed_output:
                proc = subprocess.run(
                    command,
                    stdout=compressed_output,
                    stderr=subprocess.PIPE,
                    env=env,
                    check=False,
                )
        except FileNotFoundError as exc:
            raise CommandError(
                "pg_dump is not installed or is not available in PATH."
            ) from exc

        if proc.returncode != 0:
            backup_file.unlink(missing_ok=True)
            raise CommandError(
                f"pg_dump failed with code {proc.returncode}: {proc.stderr.decode('utf-8', errors='replace')}"
            )

    def _write_sha256(self, backup_file: Path) -> str:
        digest = hashlib.sha256()
        with backup_file.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)

        checksum = digest.hexdigest()
        checksum_path = backup_file.with_suffix(backup_file.suffix + ".sha256")
        checksum_path.write_text(f"{checksum}  {backup_file.name}\n", encoding="utf-8")
        return checksum

    def _write_metadata(self, backup_file: Path, checksum: str, engine: str, now: datetime, label: str) -> None:
        metadata_path = backup_file.with_suffix(backup_file.suffix + ".json")
        metadata = {
            "file": backup_file.name,
            "checksum_sha256": checksum,
            "engine": engine,
            "created_at_utc": now.isoformat(),
            "label": label,
            "project": "Solar Quote Tool",
        }
        metadata_path.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )

    def _purge_old_backups(self, output_dir: Path, retention_hours: int) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=retention_hours)
        removed = 0

        for candidate in output_dir.glob("*.gz"):
            mtime = datetime.fromtimestamp(candidate.stat().st_mtime, tz=timezone.utc)
            if mtime >= cutoff:
                continue

            candidate.unlink(missing_ok=True)
            candidate.with_suffix(candidate.suffix + ".sha256").unlink(missing_ok=True)
            candidate.with_suffix(candidate.suffix + ".json").unlink(missing_ok=True)
            removed += 1

        return removed

    @staticmethod
    def _sanitize_label(value: str) -> str:
        cleaned = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in value.strip())
        cleaned = cleaned.strip("-")
        return cleaned or "manual"
