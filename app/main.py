# FastAPI (backend)

# To run the code in dev mode:
# source .venv/bin/activate
# fastapi dev login.py
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI

from app.routers import data_plot, login, netbank_credentials
from app.services.login_service import (  # reuse the already-initialized firebase singleton
    firebase,
)
from app.services.scheduler import scheduler

app = FastAPI(title="Bank analysis backend")


def configure_logging():
    """
    Configure application logging for the project package only.
    - LOG_LEVEL: default DEBUG
    - LOG_FILE: optional path to file (will use RotatingFileHandler)
    - If LOG_FILE is not set logs are streamed to stdout (recommended for Docker)
    """
    log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()
    log_file = os.getenv("LOG_FILE", "")

    # Use a package-level logger so the setting applies across `app.*` modules only
    project_logger = logging.getLogger("app")

    # Avoid duplicate handlers when this function is called multiple times
    if project_logger.handlers:
        for h in list(project_logger.handlers):
            project_logger.removeHandler(h)

    level = getattr(logging, log_level, logging.DEBUG)
    project_logger.setLevel(level)

    formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")

    if log_file:
        try:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        fh = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
        fh.setLevel(level)
        fh.setFormatter(formatter)
        project_logger.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(level)
    sh.setFormatter(formatter)
    project_logger.addHandler(sh)

    # Prevent messages from being propagated to the root logger (and other handlers)
    project_logger.propagate = False

    project_logger.debug(
        "Logging configured for package 'app' with level %s, output to %s",
        log_level,
        log_file or "stdout",
    )


@app.on_event("startup")
async def startup_event():
    """
    On container start, restore per-user jobs from the configured data directory,
    and load persisted per-user tokens into the Firebase singleton so DB calls can use them.
    Jobs are scheduled daily at APP_JOB_HOUR:APP_JOB_MINUTE (defaults to 18:00).
    """
    configure_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting application - restoring jobs and loading tokens")

    base_data_dir = Path(os.getenv("APP_USER_DATA_DIR", "/var/app/user_data"))
    # Use explicit daily target hour/minute instead of an interval in seconds
    target_hour = int(os.getenv("APP_JOB_HOUR", "18"))
    target_minute = int(os.getenv("APP_JOB_MINUTE", "0"))

    logger.debug("Using base data directory: %s", base_data_dir)
    logger.debug(
        "Scheduling jobs daily at %02d:%02d (local container time)",
        target_hour,
        target_minute,
    )

    # restore jobs (creates per-user folders if needed) using daily schedule
    scheduler.restore_jobs_from_dir(base_data_dir, target_hour, target_minute)
    logger.info("Restored scheduled jobs from %s", base_data_dir)

    # populate firebase.user_tokens from disk and attempt token refresh
    try:
        firebase.load_tokens_from_dir(base_data_dir, refresh=True)
        logger.info("Loaded user tokens from %s", base_data_dir)
    except Exception as exc:
        logger.exception("Failed to load tokens from dir: %s", exc)


@app.get("/")
async def root():
    logger = logging.getLogger(__name__)
    logger.info("health check - root endpoint invoked")
    return {"message": "Hello World"}


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(login.router)
app.include_router(netbank_credentials.router)
app.include_router(data_plot.router)
