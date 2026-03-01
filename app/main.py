# FastAPI (backend)

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Awaitable, Callable, Dict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response

from app.core.config import get_settings
from app.core.error_mapping import exception_to_http, get_error_response
from app.core.exceptions import AppException
from app.core.firebase_init import (
    get_credential,
    initialize_firebase_admin,
    is_testing_env,
)
from app.core.firestore_handler.QueryHandler import initialize_app
from app.core.health import get_health
from app.core.logging_config import configure_logging
from app.routers import data_plot, login, netbank_credentials
from app.services.scheduler import create_scheduler


async def stop_scheduler_on_shutdown(app: FastAPI) -> None:
    scheduler = getattr(app.state, "scheduler", None)
    if scheduler:
        await scheduler.stop_all()
        logger = logging.getLogger(__name__)
        logger.info("Scheduler stopped on application shutdown")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    logger = logging.getLogger(__name__)
    health = get_health()
    settings = get_settings()

    app.state.scheduler = None
    app.state.firebase = None

    logger.info("=" * 60)
    logger.info("Starting application startup sequence")
    logger.info("=" * 60)
    if is_testing_env():
        logger.info("Test environment detected; skipping Firebase/token initialization")
        health.mark_component_ready("scheduler", "skipped_in_tests")
        health.mark_component_ready("tokens", "skipped_in_tests")
        health.mark_component_ready("firebase", "skipped_in_tests")
        health.mark_startup_complete()
        yield
        return

    try:
        initialize_firebase_admin()

        firebase = initialize_app(
            config=get_credential(as_dict=True),
        )
        app.state.firebase = firebase

        scheduler = create_scheduler(firebase_provider=lambda: app.state.firebase)
        app.state.scheduler = scheduler

        base_data_dir = settings.app_user_data_dir
        target_hour = settings.app_job_hour
        target_minute = settings.app_job_minute

        logger.debug("Base data directory: %s", base_data_dir)
        logger.debug("Daily job scheduled at %02d:%02d", target_hour, target_minute)

        if scheduler is not None:
            scheduler.restore_jobs_from_dir(base_data_dir, target_hour, target_minute)
            health.mark_component_ready("scheduler")
            logger.info("Scheduler jobs restored successfully")
        else:
            logger.warning(
                "Scheduler lock not acquired; skipping scheduler restore in this process"
            )
            health.mark_component_ready("scheduler", "lock_not_acquired")

        try:
            firebase.load_tokens_from_dir(base_data_dir, refresh=True)
            health.mark_component_ready("tokens")
            logger.info("User tokens loaded successfully")
        except Exception as exc:
            health.mark_component_ready("tokens", str(exc))
            logger.exception("Failed to load user tokens: %s", exc)
            raise

        health.mark_component_ready("firebase")
        health.mark_startup_complete()

        logger.info("=" * 60)
        logger.info("Application startup complete")
        logger.info("=" * 60)

        yield
    except Exception as exc:
        logger.critical("Startup failed; application will not accept requests: %s", exc)
        raise
    finally:
        await stop_scheduler_on_shutdown(app)


app = FastAPI(title="Bank analysis backend", lifespan=lifespan)
app.state.scheduler = None
app.state.firebase = None


@app.middleware("http")
async def error_handling_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
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


@app.get("/")
async def root() -> Dict[str, str]:
    logger = logging.getLogger(__name__)
    logger.debug("Root endpoint invoked")
    return {"message": "Bank Analysis Backend"}


@app.get("/health")
async def health_check() -> JSONResponse:
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
