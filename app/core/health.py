"""Readiness and liveness health checks.
Tracks startup completion and dependency health.
"""

import importlib.metadata
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib import error, request
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger(__name__)


class HealthStatus:
    """Track application readiness and component health."""

    def __init__(self) -> None:
        self.is_ready = False
        self._startup_time = datetime.now(timezone.utc)
        self.startup_complete_time: Optional[datetime] = None
        self.components: Dict[str, Dict[str, Any]] = {
            "firebase": {"ready": False, "error": None},
            "scheduler": {"ready": False, "error": None},
            "tokens": {"ready": False, "error": None},
            "selenium": {"ready": False, "error": None},
        }

    def mark_startup_complete(self) -> None:
        """Mark startup phase as complete."""
        self.is_ready = True
        self.startup_complete_time = datetime.now(timezone.utc)
        logger.info("Application startup complete and ready to serve requests")

    def mark_component_ready(self, component: str, error: Optional[str] = None) -> None:
        """Mark a component as ready or failed."""
        if component not in self.components:
            logger.warning("Unknown component '%s'", component)
            return
        self.components[component]["ready"] = error is None
        self.components[component]["error"] = error
        status = "ready" if error is None else f"failed ({error})"
        logger.info("Component '%s' is %s", component, status)

    def get_status(self) -> Dict[str, Any]:
        """Return health status for /health endpoint."""
        uptime = (datetime.now(timezone.utc) - self._startup_time).total_seconds()
        try:
            version = importlib.metadata.version("bab")
        except importlib.metadata.PackageNotFoundError:
            version = "unknown"
        return {
            "ready": self.is_ready,
            "startup_complete_time": (
                self.startup_complete_time.isoformat()
                if self.startup_complete_time
                else None
            ),
            "components": self.components,
            "uptime_seconds": round(uptime, 2),
            "version": version,
        }


# Global health instance
_health = HealthStatus()


def get_health() -> HealthStatus:
    """Retrieve the global health tracker."""
    return _health


def _build_status_urls(remote_url: str) -> list[str]:
    parsed = urlparse(remote_url)
    base_path = parsed.path.rstrip("/")

    candidates: list[str] = []
    if base_path.endswith("/status"):
        candidates.append(remote_url)
    else:
        status_path = f"{base_path}/status" if base_path else "/status"
        candidates.append(
            urlunparse(
                (
                    parsed.scheme,
                    parsed.netloc,
                    status_path,
                    "",
                    "",
                    "",
                )
            )
        )
        if base_path in {"", "/"}:
            candidates.append(
                urlunparse(
                    (
                        parsed.scheme,
                        parsed.netloc,
                        "/wd/hub/status",
                        "",
                        "",
                        "",
                    )
                )
            )
    return candidates


def probe_selenium_readiness() -> Optional[str]:
    """Return None when Selenium is reachable and ready; otherwise an error code."""
    remote_url = os.getenv("SELENIUM_REMOTE_URL", "http://selenium:4444")
    timeout_raw = os.getenv("SELENIUM_PROBE_TIMEOUT_SECONDS", "1.0")
    try:
        timeout_seconds = max(0.1, min(float(timeout_raw), 5.0))
    except ValueError:
        timeout_seconds = 1.0

    for status_url in _build_status_urls(remote_url):
        try:
            with request.urlopen(status_url, timeout=timeout_seconds) as response:
                if response.status >= 400:
                    continue
                payload = response.read().decode("utf-8", errors="ignore")
                if not payload:
                    return None
                try:
                    import json

                    data = json.loads(payload)
                except json.JSONDecodeError:
                    return None

                value = data.get("value") if isinstance(data, dict) else None
                ready_value = None
                if isinstance(value, dict):
                    ready_value = value.get("ready")
                elif isinstance(data, dict):
                    ready_value = data.get("ready")

                if ready_value is False:
                    return "not_ready"
                return None
        except error.HTTPError:
            continue
        except error.URLError:
            continue
        except TimeoutError:
            continue
        except Exception:
            continue
    return "unreachable"
