"""Tests for feature enhancements: health, /user/me email, password-reset,
CSV/Parquet support, pagination, job-status, error timestamps, cleanup-metrics."""

import os

os.environ.setdefault("APP_ALLOW_UNSAFE_DESERIALIZE", "true")

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import app.core.health as health_mod
import pandas as pd
import pytest
from app.core.auth import get_current_user, get_current_user_id, get_firebase_dep
from app.main import app
from app.routers.login import get_scheduler_dep
from fastapi.testclient import TestClient

# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _setup(monkeypatch):
    """Reset health, override deps, and clean up after each test."""
    monkeypatch.setenv("PYTEST_RUNNING", "1")

    h = health_mod._health
    h.is_ready = False
    h.startup_complete_time = None
    for comp in h.components.values():
        comp["ready"] = False
        comp["error"] = None

    app.state.scheduler = None
    app.state.firebase = None
    app.state.deletion_worker = None

    yield

    app.dependency_overrides.clear()
    h.is_ready = False
    h.startup_complete_time = None


@pytest.fixture()
def mock_deps():
    """Override auth + infra deps and return (scheduler_mock, firebase_mock)."""
    mock_scheduler = MagicMock()
    mock_firebase = MagicMock()
    app.dependency_overrides[get_current_user_id] = lambda: "test_user"
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": "test_user",
        "email": "test@example.com",
    }
    app.dependency_overrides[get_scheduler_dep] = lambda: mock_scheduler
    app.dependency_overrides[get_firebase_dep] = lambda: mock_firebase
    yield mock_scheduler, mock_firebase


client = TestClient(app, raise_server_exceptions=False)


# ── 1. Enhanced /health ────────────────────────────────────────────────────


class TestHealthEndpoint:
    def test_health_ready_includes_version_and_uptime(self):
        h = health_mod.get_health()
        h.mark_startup_complete()

        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "healthy"
        assert "version" in body
        assert isinstance(body["version"], str)
        assert "uptime_seconds" in body
        assert isinstance(body["uptime_seconds"], (int, float))
        assert body["uptime_seconds"] >= 0

    def test_health_not_ready_omits_version_and_uptime(self):
        r = client.get("/health")
        assert r.status_code == 503
        body = r.json()
        assert body["status"] == "not_ready"
        # 503 response does not include version/uptime
        assert "version" not in body
        assert "uptime_seconds" not in body

    def test_health_status_get_status_has_version_and_uptime(self):
        h = health_mod.get_health()
        status = h.get_status()
        assert "version" in status
        assert "uptime_seconds" in status
        assert status["uptime_seconds"] >= 0


# ── 2. Enhanced /user/me ──────────────────────────────────────────────────


class TestUserMe:
    def test_me_returns_email(self, mock_deps):
        r = client.get("/user/me")
        assert r.status_code == 200
        body = r.json()
        assert body["user_id"] == "test_user"
        assert body["email"] == "test@example.com"

    def test_me_returns_null_email_when_absent(self, mock_deps):
        app.dependency_overrides[get_current_user] = lambda: {
            "user_id": "test_user",
            "email": None,
        }
        r = client.get("/user/me")
        assert r.status_code == 200
        body = r.json()
        assert body["user_id"] == "test_user"
        assert body["email"] is None


# ── 3. Password reset ────────────────────────────────────────────────────


class TestPasswordReset:
    def test_password_reset_success(self, mock_deps):
        _, mock_firebase = mock_deps
        mock_auth = MagicMock()
        mock_firebase.auth.return_value = (mock_auth, None)

        with patch("app.services.login_service.request_password_reset") as mock_reset:
            mock_reset.return_value = {
                "message": "If the email is registered, a password reset link has been sent."
            }
            r = client.post(
                "/user/password-reset",
                json={"email": "user@example.com"},
            )
        assert r.status_code == 200
        assert "password reset link" in r.json()["message"].lower()

    def test_password_reset_still_returns_200_on_failure(self, mock_deps):
        """Endpoint always returns 200 to prevent email enumeration."""
        with patch(
            "app.routers.login.request_password_reset",
            side_effect=Exception("firebase error"),
        ):
            r = client.post(
                "/user/password-reset",
                json={"email": "unknown@example.com"},
            )
        assert r.status_code == 200
        assert "password reset link" in r.json()["message"].lower()

    def test_password_reset_invalid_email_returns_422(self, mock_deps):
        r = client.post(
            "/user/password-reset",
            json={"email": "not-an-email"},
        )
        assert r.status_code == 422


# ── 4. CSV and Parquet filename validation ────────────────────────────────


class TestFilenameValidation:
    def test_csv_filename_accepted(self, mock_deps, tmp_path):
        base = tmp_path / "userdata"
        user_dir = base / "test_user"
        user_dir.mkdir(parents=True)
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        df.to_csv(user_dir / "data.csv", index=False)

        with patch("app.routers.data_plot._base_dir", return_value=base):
            r = client.get("/data/files/data.csv/preview")
        assert r.status_code == 200
        assert "preview" in r.json()

    def test_parquet_filename_accepted(self, mock_deps, tmp_path):
        base = tmp_path / "userdata"
        user_dir = base / "test_user"
        user_dir.mkdir(parents=True)
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        df.to_parquet(user_dir / "data.parquet")

        with patch("app.routers.data_plot._base_dir", return_value=base):
            r = client.get("/data/files/data.parquet/preview")
        assert r.status_code == 200
        assert "preview" in r.json()

    def test_unsupported_extension_rejected(self, mock_deps):
        with patch("app.routers.data_plot._base_dir", return_value=Path("/tmp")):
            r = client.get("/data/files/data.xlsx/preview")
        assert r.status_code == 400

    def test_csv_series_extraction(self, mock_deps, tmp_path):
        base = tmp_path / "userdata"
        user_dir = base / "test_user"
        user_dir.mkdir(parents=True)
        df = pd.DataFrame({"x": [1, 2, 3], "y": [10.0, 20.0, 30.0]})
        df.to_csv(user_dir / "series.csv", index=False)

        with patch("app.routers.data_plot._base_dir", return_value=base):
            r = client.get("/data/files/series.csv/series", params={"y": "y"})
        assert r.status_code == 200
        data = r.json()
        assert "x" in data and "y" in data
        assert len(data["y"]) == 3


# ── 5. File list pagination ──────────────────────────────────────────────


class TestFileListPagination:
    def test_pagination_returns_total_count(self, mock_deps, tmp_path):
        base = tmp_path / "userdata"
        user_dir = base / "test_user"
        user_dir.mkdir(parents=True)
        for i in range(5):
            pd.DataFrame({"v": [i]}).to_pickle(user_dir / f"f{i}.pkl")

        with patch("app.routers.data_plot._base_dir", return_value=base):
            r = client.get("/data/list", params={"offset": 0, "limit": 3})
        assert r.status_code == 200
        body = r.json()
        assert body["total_count"] == 5
        assert len(body["files"]) == 3

    def test_pagination_offset(self, mock_deps, tmp_path):
        base = tmp_path / "userdata"
        user_dir = base / "test_user"
        user_dir.mkdir(parents=True)
        for i in range(5):
            pd.DataFrame({"v": [i]}).to_pickle(user_dir / f"f{i}.pkl")

        with patch("app.routers.data_plot._base_dir", return_value=base):
            r = client.get("/data/list", params={"offset": 3, "limit": 10})
        assert r.status_code == 200
        body = r.json()
        assert body["total_count"] == 5
        assert len(body["files"]) == 2  # only 2 remaining after offset 3

    def test_pagination_default_limit(self, mock_deps, tmp_path):
        base = tmp_path / "userdata"
        user_dir = base / "test_user"
        user_dir.mkdir(parents=True)
        pd.DataFrame({"v": [1]}).to_pickle(user_dir / "single.pkl")

        with patch("app.routers.data_plot._base_dir", return_value=base):
            r = client.get("/data/list")
        assert r.status_code == 200
        body = r.json()
        assert "total_count" in body
        assert body["total_count"] == 1

    def test_pagination_mixed_formats(self, mock_deps, tmp_path):
        """Pagination works across pickle, CSV, and Parquet files."""
        base = tmp_path / "userdata"
        user_dir = base / "test_user"
        user_dir.mkdir(parents=True)
        df = pd.DataFrame({"v": [1]})
        df.to_pickle(user_dir / "a.pkl")
        df.to_csv(user_dir / "b.csv", index=False)
        df.to_parquet(user_dir / "c.parquet")

        with patch("app.routers.data_plot._base_dir", return_value=base):
            r = client.get("/data/list", params={"offset": 0, "limit": 100})
        assert r.status_code == 200
        body = r.json()
        assert body["total_count"] == 3
        filenames = [f["filename"] for f in body["files"]]
        assert "a.pkl" in filenames
        assert "b.csv" in filenames
        assert "c.parquet" in filenames


# ── 6. Job status ────────────────────────────────────────────────────────


class TestJobStatus:
    def test_job_status_with_scheduled_job(self, mock_deps, tmp_path, monkeypatch):
        mock_scheduler, _ = mock_deps
        mock_scheduler.get_next_run_for_user.return_value = {
            "seconds_until_next_run": 3600,
            "next_run_timestamp_ms": 9999999,
        }
        monkeypatch.setenv("APP_USER_DATA_DIR", str(tmp_path))
        # Reset cached settings so the new env var is picked up
        import app.core.config as config_mod

        config_mod._SETTINGS = None

        user_dir = tmp_path / "test_user"
        user_dir.mkdir(parents=True, exist_ok=True)

        r = client.get("/user/job-status")
        assert r.status_code == 200
        body = r.json()
        assert body["user_id"] == "test_user"
        assert body["has_scheduled_job"] is True
        assert body["next_run"]["seconds_until_next_run"] == 3600
        assert body["deletion_pending"] is False

        config_mod._SETTINGS = None  # reset for other tests

    def test_job_status_no_job(self, mock_deps, tmp_path, monkeypatch):
        mock_scheduler, _ = mock_deps
        mock_scheduler.get_next_run_for_user.return_value = None
        monkeypatch.setenv("APP_USER_DATA_DIR", str(tmp_path))
        import app.core.config as config_mod

        config_mod._SETTINGS = None

        r = client.get("/user/job-status")
        assert r.status_code == 200
        body = r.json()
        assert body["has_scheduled_job"] is False
        assert body["next_run"] is None

        config_mod._SETTINGS = None


# ── 7. Error response timestamps ─────────────────────────────────────────


class TestErrorTimestamp:
    def test_exception_to_http_includes_timestamp(self):
        from app.core.error_mapping import exception_to_http
        from app.core.exceptions import FileNotFoundError

        exc = FileNotFoundError("test.pkl")
        http_exc = exception_to_http(exc)
        detail = http_exc.detail
        assert "timestamp" in detail
        # Verify it's a valid ISO timestamp
        datetime.fromisoformat(detail["timestamp"])

    def test_get_error_response_includes_timestamp(self):
        from app.core.error_mapping import get_error_response

        resp = get_error_response(RuntimeError("boom"))
        assert "timestamp" in resp
        datetime.fromisoformat(resp["timestamp"])

    def test_generic_exception_to_http_includes_timestamp(self):
        from app.core.error_mapping import exception_to_http

        http_exc = exception_to_http(RuntimeError("oops"))
        detail = http_exc.detail
        assert "timestamp" in detail
        datetime.fromisoformat(detail["timestamp"])

    def test_app_exception_get_error_response_includes_timestamp(self):
        from app.core.error_mapping import get_error_response
        from app.core.exceptions import LoginFailedError

        resp = get_error_response(LoginFailedError())
        assert "timestamp" in resp
        datetime.fromisoformat(resp["timestamp"])


# ── 8. Cleanup metrics ──────────────────────────────────────────────────


class TestCleanupMetrics:
    def test_cleanup_metrics_returns_503_when_no_worker(self):
        app.state.deletion_worker = None
        r = client.get("/admin/cleanup-metrics")
        assert r.status_code == 503

    def test_cleanup_metrics_returns_200_with_worker(self):
        from app.services.user_deletion_service import DeletionWorker

        worker = DeletionWorker(
            base_dir=Path("/tmp/nonexistent"), check_interval_seconds=9999
        )
        app.state.deletion_worker = worker

        r = client.get("/admin/cleanup-metrics")
        assert r.status_code == 200
        body = r.json()
        assert "last_run_at" in body
        assert "total_deleted" in body
        assert "total_errors" in body
        assert "total_scans" in body
        assert body["total_scans"] == 0
        assert body["total_deleted"] == 0
        assert body["total_errors"] == 0

    def test_cleanup_metrics_tracks_scans(self, tmp_path):
        from app.services.user_deletion_service import DeletionWorker

        worker = DeletionWorker(base_dir=tmp_path, check_interval_seconds=9999)
        # Manually call _run logic via execute_expired_deletions
        from app.services.user_deletion_service import execute_expired_deletions

        execute_expired_deletions(tmp_path)

        # Simulate what _run does
        worker._metrics["total_scans"] += 1
        worker._metrics["last_run_at"] = datetime.now(timezone.utc).isoformat()

        app.state.deletion_worker = worker
        r = client.get("/admin/cleanup-metrics")
        assert r.status_code == 200
        body = r.json()
        assert body["total_scans"] == 1
        assert body["last_run_at"] is not None


# ── 9. Backward compatibility ────────────────────────────────────────────


class TestBackwardCompatibility:
    def test_list_pickles_for_user_alias_exists(self):
        from app.services.data_service import (
            list_data_files_for_user,
            list_pickles_for_user,
        )

        assert list_pickles_for_user is list_data_files_for_user

    def test_get_current_user_id_still_returns_str(self, mock_deps):
        """get_current_user_id override returns str, not dict."""
        # The override returns "test_user" (a str)
        r = client.get("/user/next_run")
        # We just need to confirm the dependency resolved without error
        # (it will be 404 because mock scheduler returns None by default)
        assert r.status_code in (200, 404)
