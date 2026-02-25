# FastAPI (backend)

import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.error_mapping import exception_to_http, get_error_response
from app.core.exceptions import AppException
from app.core.firebase_init import is_testing_env
from app.core.health import get_health
from app.core.logging_config import configure_logging
from app.routers import data_plot, login, netbank_credentials
from app.services.login_service import get_firebase
from app.services.scheduler import scheduler

app = FastAPI(title="Bank analysis backend")


@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    """Catch unhandled exceptions and return structured error responses."""
    try:
        return await call_next(request)
    except AppException as exc:
        logger = logging.getLogger(__name__)
        logger.exception("Handled application exception")
        http_exc = exception_to_http(exc)
        return JSONResponse(status_code=http_exc.status_code, content=http_exc.detail)
    except Exception as exc:
        logger = logging.getLogger(__name__)
        logger.exception("Unhandled exception in request")
        return JSONResponse(
            status_code=500,
            content=get_error_response(exc),
        )


@app.on_event("startup")
async def startup_event():
    """
    Readiness-aware startup: configure logging, restore jobs, load tokens.
    Marks application ready only after all components are initialized.
    Fails fast on configuration errors.
    """
    configure_logging()
    logger = logging.getLogger(__name__)
    health = get_health()

    logger.info("=" * 60)
    logger.info("Starting application startup sequence")
    logger.info("=" * 60)

    try:
        if is_testing_env():
            logger.info(
                "Test environment detected; skipping Firebase/token initialization"
            )
            health.mark_component_ready("scheduler", "skipped_in_tests")
            health.mark_component_ready("tokens", "skipped_in_tests")
            health.mark_component_ready("firebase", "skipped_in_tests")
            health.mark_startup_complete()
            return

        base_data_dir = Path(os.getenv("APP_USER_DATA_DIR", "/var/app/user_data"))
        target_hour = int(os.getenv("APP_JOB_HOUR", "18"))
        target_minute = int(os.getenv("APP_JOB_MINUTE", "0"))

        logger.debug("Base data directory: %s", base_data_dir)
        logger.debug("Daily job scheduled at %02d:%02d", target_hour, target_minute)

        # Restore scheduler jobs
        if scheduler is not None:
            scheduler.restore_jobs_from_dir(base_data_dir, target_hour, target_minute)
            health.mark_component_ready("scheduler")
            logger.info("Scheduler jobs restored successfully")
        else:
            logger.warning(
                "Scheduler lock not acquired; skipping scheduler restore in this process"
            )

        firebase = get_firebase()
        # Load persisted tokens
        try:
            firebase.load_tokens_from_dir(base_data_dir, refresh=True)
            health.mark_component_ready("tokens")
            logger.info("User tokens loaded successfully")
        except Exception as exc:
            health.mark_component_ready("tokens", str(exc))
            logger.exception("Failed to load user tokens: %s", exc)
            raise

        # Mark Firebase as ready (was initialized at import time)
        health.mark_component_ready("firebase")

        # All components ready
        health.mark_startup_complete()

        logger.info("=" * 60)
        logger.info("Application startup complete")
        logger.info("=" * 60)

    except Exception as exc:
        logger.critical("Startup failed; application will not accept requests: %s", exc)
        raise


@app.get("/")
async def root():
    logger = logging.getLogger(__name__)
    logger.debug("Root endpoint invoked")
    return {"message": "Bank Analysis Backend"}


@app.get("/health")
async def health_check():
    """
    Liveness and readiness probe.
    Returns 200 only if application is ready; components are healthy.
    Clients should not route traffic until this returns ready=true.
    """
    health = get_health()
    status = health.get_status()

    if not health.is_ready:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "ready": False,
                "components": status["components"],
            },
        )

    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "ready": True,
            "startup_complete_time": status["startup_complete_time"],
            "components": status["components"],
        },
    )


app.include_router(login.router)
app.include_router(netbank_credentials.router)
app.include_router(data_plot.router)
