"""
Scheduler — runs the briefing 3x daily using APScheduler.
Designed to run as the main process in a Docker container.
"""
import logging
import signal
import sys
import time

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

import config
from orchestrator import run_briefing

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("scheduler")


def briefing_job():
    try:
        run_briefing(dry_run=False)
    except Exception as e:
        log.error("Briefing job failed: %s", e, exc_info=True)


def main():
    tz = pytz.timezone(config.TIMEZONE)
    scheduler = BackgroundScheduler(timezone=tz)

    # Morning briefing
    scheduler.add_job(
        briefing_job,
        trigger=CronTrigger(hour=config.MORNING_HOUR, minute=0, timezone=tz),
        id="morning_briefing",
        name="Morning Briefing",
        replace_existing=True,
    )

    # Midday briefing
    scheduler.add_job(
        briefing_job,
        trigger=CronTrigger(hour=config.LUNCH_HOUR, minute=0, timezone=tz),
        id="midday_briefing",
        name="Midday Briefing",
        replace_existing=True,
    )

    # Evening briefing
    scheduler.add_job(
        briefing_job,
        trigger=CronTrigger(hour=config.EVENING_HOUR, minute=0, timezone=tz),
        id="evening_briefing",
        name="Evening Briefing",
        replace_existing=True,
    )

    scheduler.start()
    log.info("Scheduler started. Timezone: %s", config.TIMEZONE)
    log.info(
        "Schedule: %02d:00 (morning) | %02d:00 (midday) | %02d:00 (evening)",
        config.MORNING_HOUR,
        config.LUNCH_HOUR,
        config.EVENING_HOUR,
    )

    # Print next run times
    for job in scheduler.get_jobs():
        log.info("  Job '%s' — next run: %s", job.name, job.next_run_time)

    # Graceful shutdown on SIGTERM / SIGINT
    def shutdown(signum, frame):
        log.info("Shutting down scheduler...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    # Keep the process alive
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
