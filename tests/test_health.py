"""Tests for app.core.health – HealthStatus."""

from app.core.health import HealthStatus, get_health

# ── HealthStatus ───────────────────────────────────────────────────────────


def test_health_initial_state():
    h = HealthStatus()
    assert h.is_ready is False
    assert h.startup_complete_time is None
    assert "firebase" in h.components
    assert "scheduler" in h.components
    assert "tokens" in h.components


def test_mark_startup_complete():
    h = HealthStatus()
    h.mark_startup_complete()
    assert h.is_ready is True
    assert h.startup_complete_time is not None


def test_mark_component_ready_success():
    h = HealthStatus()
    h.mark_component_ready("firebase")
    assert h.components["firebase"]["ready"] is True
    assert h.components["firebase"]["error"] is None


def test_mark_component_ready_with_error():
    h = HealthStatus()
    h.mark_component_ready("scheduler", "connection refused")
    assert h.components["scheduler"]["ready"] is False
    assert h.components["scheduler"]["error"] == "connection refused"


def test_mark_component_ready_unknown_component_is_noop():
    h = HealthStatus()
    # should not raise
    h.mark_component_ready("nonexistent_component")
    assert "nonexistent_component" not in h.components


def test_get_status_before_ready():
    h = HealthStatus()
    status = h.get_status()
    assert status["ready"] is False
    assert status["startup_complete_time"] is None
    assert isinstance(status["components"], dict)


def test_get_status_after_ready():
    h = HealthStatus()
    h.mark_startup_complete()
    status = h.get_status()
    assert status["ready"] is True
    assert status["startup_complete_time"] is not None
    # iso format check
    assert "T" in status["startup_complete_time"]


def test_get_status_includes_all_components():
    h = HealthStatus()
    status = h.get_status()
    assert set(status["components"].keys()) == {"firebase", "scheduler", "tokens"}


def test_get_health_returns_singleton():
    h1 = get_health()
    h2 = get_health()
    assert h1 is h2


def test_full_startup_sequence():
    h = HealthStatus()
    h.mark_component_ready("firebase")
    h.mark_component_ready("scheduler")
    h.mark_component_ready("tokens")
    h.mark_startup_complete()

    status = h.get_status()
    assert status["ready"] is True
    for comp in ["firebase", "scheduler", "tokens"]:
        assert status["components"][comp]["ready"] is True
