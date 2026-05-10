"""Security-focused tests for getReport directory permission handling."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from app.core.netbank.getReport import ErsteNetBroker
from app.core.netbank.utils import reportFormatter


def test_config_edge_uses_owner_only_directory_permissions(tmp_path):
    broker = ErsteNetBroker.__new__(ErsteNetBroker)
    broker._ErsteNetBroker__SAVE_TO = tmp_path / "save"
    broker._ErsteNetBroker__REMOTE_DIR = tmp_path / "remote"
    broker._ErsteNetBroker__LOCAL_DIR = tmp_path / "local"

    with (
        patch("app.core.netbank.getReport.os.makedirs"),
        patch("app.core.netbank.getReport.os.chmod") as mock_chmod,
        patch("app.core.netbank.getReport.webdriver.Remote", return_value=MagicMock()),
    ):
        broker._config_edge()

    assert mock_chmod.call_count == 2
    for call in mock_chmod.call_args_list:
        assert call.args[1] == 0o700


def test_rename_downloaded_file_prefers_most_recent_mtime(tmp_path):
    broker = ErsteNetBroker.__new__(ErsteNetBroker)
    save_dir = tmp_path / "save"
    local_dir = tmp_path / "local"
    save_dir.mkdir()
    local_dir.mkdir()

    old_file = local_dir / "old.xls"
    new_file = local_dir / "new.xls"
    old_file.write_text("old")
    new_file.write_text("new")

    broker._ErsteNetBroker__SAVE_TO = save_dir
    broker._ErsteNetBroker__LOCAL_DIR = local_dir

    def _mtime(path_str: str) -> int:
        name = Path(path_str).name
        return 2 if name == "new.xls" else 1

    with patch("app.core.netbank.getReport.os.path.getmtime", side_effect=_mtime):
        renamed = broker._renameDownloadedFile(timeout=1)

    assert renamed.startswith("Riport_")
    assert renamed.endswith(".xls")
    assert (save_dir / renamed).exists()
    assert old_file.exists()
    assert not new_file.exists()


def test_handle_already_logged_in_exception_keeps_checksession_signal():
    broker = ErsteNetBroker.__new__(ErsteNetBroker)
    driver = MagicMock()
    driver.current_url = "https://example/checksession"
    broker.driver = driver

    with patch.object(
        ErsteNetBroker,
        "_ErsteNetBroker__find_and_click",
        side_effect=RuntimeError("click failed"),
    ):
        assert broker._handle_already_logged_in_Selenium() is True


def test_report_formatter_requires_valid_fileloc_when_default_is_unset():
    with pytest.raises(ValueError, match="fileLoc is required"):
        reportFormatter()

    with pytest.raises(ValueError, match="non-empty path"):
        reportFormatter(fileLoc="   ")
