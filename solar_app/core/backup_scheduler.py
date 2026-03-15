"""
Automatic database backup scheduler using APScheduler.
Integrates backup routines into Django app lifecycle.
"""
import logging
import os
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from django.conf import settings
from django.core.management import call_command

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: BackgroundScheduler | None = None


def get_scheduler_config() -> dict:
    """
    Get backup scheduler configuration.
    
    Returns:
        dict: Configuration for hourly and monthly backup schedules.
              Can be customized via environment variables.
    """
    return {
        'hourly': {
            'label': 'hourly',
            'retention_hours': int(os.getenv('BACKUP_RETENTION_HOURS', '168')),  # 7 days
            'interval': int(os.getenv('BACKUP_INTERVAL_HOURS', '1')),  # Every hour
            'enabled': os.getenv('BACKUP_HOURLY_ENABLED', 'true').lower() == 'true',
        },
        'monthly': {
            'label': 'monthly',
            'retention_hours': int(os.getenv('BACKUP_RETENTION_MONTHS', '2592')),  # 3 months
            'day_of_month': int(os.getenv('BACKUP_MONTHLY_DAY', '1')),  # 1st of month
            'hour': int(os.getenv('BACKUP_MONTHLY_HOUR', '3')),  # 3:00 AM
            'minute': int(os.getenv('BACKUP_MONTHLY_MINUTE', '30')),  # 3:30 AM
            'enabled': os.getenv('BACKUP_MONTHLY_ENABLED', 'true').lower() == 'true',
        },
        'monthly_restore_drill': {
            'label': 'monthly_restore_drill',
            'day_of_month': int(os.getenv('BACKUP_DRILL_DAY', '15')),  # 15th of month
            'hour': int(os.getenv('BACKUP_DRILL_HOUR', '4')),  # 4:00 AM
            'minute': int(os.getenv('BACKUP_DRILL_MINUTE', '0')),  # 4:00 AM
            'enabled': os.getenv('BACKUP_MONTHLY_DRILL_ENABLED', 'false').lower() == 'true',
        },
    }


def _run_hourly_backup():
    """Execute hourly backup job."""
    config = get_scheduler_config()
    hourly_cfg = config['hourly']
    
    logger.info(f"[Backup Scheduler] Starting hourly backup at {datetime.now(timezone.utc).isoformat()}")
    
    try:
        call_command(
            'backup_db',
            label=hourly_cfg['label'],
            retention_hours=hourly_cfg['retention_hours'],
        )
        logger.info(f"[Backup Scheduler] Hourly backup completed successfully")
    except Exception as e:
        logger.error(f"[Backup Scheduler] Hourly backup failed: {e}", exc_info=True)


def _run_monthly_backup():
    """Execute monthly backup job."""
    config = get_scheduler_config()
    monthly_cfg = config['monthly']
    
    logger.info(f"[Backup Scheduler] Starting monthly backup at {datetime.now(timezone.utc).isoformat()}")
    
    try:
        call_command(
            'backup_db',
            label=monthly_cfg['label'],
            retention_hours=monthly_cfg['retention_hours'],
        )
        logger.info(f"[Backup Scheduler] Monthly backup completed successfully")
    except Exception as e:
        logger.error(f"[Backup Scheduler] Monthly backup failed: {e}", exc_info=True)


def _run_monthly_restore_drill():
    """Execute monthly restore drill to validate backup integrity and procedures."""
    config = get_scheduler_config()
    drill_cfg = config['monthly_restore_drill']
    
    logger.info(f"[Backup Scheduler] Starting monthly restore drill at {datetime.now(timezone.utc).isoformat()}")
    
    try:
        from pathlib import Path
        
        # 1. Create pre-drill guard backup
        logger.info("[Backup Scheduler] Creating pre-drill guard backup")
        call_command(
            'backup_db',
            label='pre_restore_drill_guard',
            retention_hours=2592,  # 3 months
        )
        
        # 2. Find most recent non-guard backup
        backup_dir = Path(os.getenv('BACKUP_DIR', settings.BASE_DIR / 'backups'))
        backup_files = sorted([f for f in backup_dir.glob('*.gz') if 'guard' not in f.name])
        
        if not backup_files:
            logger.error("[Backup Scheduler] No backup files found for restore drill")
            return
        
        restore_file = backup_files[-1]  # Most recent
        logger.info(f"[Backup Scheduler] Restoring from backup: {restore_file.name}")
        
        # 3. Restore from backup
        call_command(
            'restore_db',
            str(restore_file),
            yes_i_know=True,
        )
        
        # 4. Run Django health check
        logger.info("[Backup Scheduler] Running Django health check")
        call_command('check')
        
        logger.info(f"[Backup Scheduler] Monthly restore drill completed successfully")
        
    except Exception as e:
        logger.error(f"[Backup Scheduler] Monthly restore drill failed: {e}", exc_info=True)


def start_scheduler() -> bool:
    """
    Start the background backup scheduler.
    
    Returns:
        bool: True if scheduler started successfully, False otherwise.
    """
    global _scheduler
    
    if _scheduler and _scheduler.running:
        logger.info("[Backup Scheduler] Scheduler already running")
        return True
    
    try:
        config = get_scheduler_config()
        
        # Initialize scheduler
        _scheduler = BackgroundScheduler(daemon=True)
        
        # Add hourly backup job
        if config['hourly']['enabled']:
            _scheduler.add_job(
                _run_hourly_backup,
                trigger=IntervalTrigger(hours=config['hourly']['interval']),
                id='backup_hourly',
                name='Hourly Database Backup',
                replace_existing=True,
            )
            logger.info(f"[Backup Scheduler] Scheduled hourly backup every {config['hourly']['interval']} hour(s)")
        
        # Add monthly backup job
        if config['monthly']['enabled']:
            _scheduler.add_job(
                _run_monthly_backup,
                trigger=CronTrigger(
                    day=config['monthly']['day_of_month'],
                    hour=config['monthly']['hour'],
                    minute=config['monthly']['minute'],
                ),
                id='backup_monthly',
                name='Monthly Database Backup',
                replace_existing=True,
            )
            logger.info(
                f"[Backup Scheduler] Scheduled monthly backup "
                f"at {config['monthly']['hour']:02d}:{config['monthly']['minute']:02d} "
                f"on day {config['monthly']['day_of_month']}"
            )
        
        # Add monthly restore drill job
        if config['monthly_restore_drill']['enabled']:
            _scheduler.add_job(
                _run_monthly_restore_drill,
                trigger=CronTrigger(
                    day=config['monthly_restore_drill']['day_of_month'],
                    hour=config['monthly_restore_drill']['hour'],
                    minute=config['monthly_restore_drill']['minute'],
                ),
                id='backup_restore_drill',
                name='Monthly Restore Drill',
                replace_existing=True,
            )
            logger.info(
                f"[Backup Scheduler] Scheduled monthly restore drill "
                f"at {config['monthly_restore_drill']['hour']:02d}:{config['monthly_restore_drill']['minute']:02d} "
                f"on day {config['monthly_restore_drill']['day_of_month']}"
            )
        
        _scheduler.start()
        logger.info("[Backup Scheduler] Background scheduler started successfully")
        return True
        
    except Exception as e:
        logger.error(f"[Backup Scheduler] Failed to start scheduler: {e}", exc_info=True)
        return False


def stop_scheduler() -> bool:
    """
    Stop the background scheduler gracefully.
    
    Returns:
        bool: True if scheduler stopped successfully.
    """
    global _scheduler
    
    try:
        if _scheduler:
            _scheduler.shutdown(wait=True)
            _scheduler = None
            logger.info("[Backup Scheduler] Background scheduler stopped")
            return True
        return True
    except Exception as e:
        logger.error(f"[Backup Scheduler] Error stopping scheduler: {e}", exc_info=True)
        return False


def get_scheduler_status() -> dict:
    """
    Get current scheduler status and next scheduled jobs.
    
    Returns:
        dict: Status information including running state and next job times.
    """
    global _scheduler
    
    if not _scheduler:
        return {
            'running': False,
            'jobs': [],
        }
    
    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
        })
    
    return {
        'running': _scheduler.running,
        'jobs': jobs,
    }
