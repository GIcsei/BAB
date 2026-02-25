"""
Readiness and liveness health checks.
Tracks startup completion and dependency health.
"""

import logging
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger(__name__)


class HealthStatus:
    """Track application readiness and component health."""

    def __init__(self):
        self.is_ready = False
        self.startup_complete_time: datetime = None
        self.components: Dict[str, Dict[str, Any]] = {
            "firebase": {"ready": False, "error": None},
            "scheduler": {"ready": False, "error": None},
            "tokens": {"ready": False, "error": None},
        }

    def mark_startup_complete(self):
        """Mark startup phase as complete."""
        self.is_ready = True
        self.startup_complete_time = datetime.utcnow()
        logger.info("Application startup complete and ready to serve requests")

    def mark_component_ready(self, component: str, error: str = None):
        """Mark a component as ready or failed."""
        if component in self.components:
            self.components[component]["ready"] = error is None
            self.components[component]["error"] = error
            status = "ready" if error is None else f"failed ({error})"
            logger.info("Component '%s' is %s", component, status)

    def get_status(self) -> Dict[str, Any]:
        """Return health status for /health endpoint."""
        return {
            "ready": self.is_ready,
            "startup_complete_time": (
                self.startup_complete_time.isoformat()
                if self.startup_complete_time
                else None
            ),
            "components": self.components,
        }


# Global health instance
_health = HealthStatus()


def get_health() -> HealthStatus:
    """Retrieve the global health tracker."""
    return _health
