import glob
import logging
import os
import os.path
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from app.core.config import get_settings
from app.core.firestore_handler.QueryHandler import Firebase
from app.core.netbank.credentials import load_user_credentials
from app.core.netbank.utils import (
    extract_date_from_filename,
    get_all_files_from_folder,
    is_today_in,
    reportFormatter,
)

logger = logging.getLogger(__name__)


class ErsteNetBroker:
    """
    Lightweight wrapper that uses Selenium to drive NetBroker and download a report.
    Credentials are loaded from an encrypted local store tied to this class and the user id;
    save them via the secured FastAPI endpoint implemented in app.routers.netbank_credentials.
    """

    def __init__(
        self,
        user_id: str,
        saveFolder: str = "/tmp/Erste",
        config_dir: Optional[str] = None,
    ) -> None:
        if not user_id:
            raise ValueError("user_id is required to load per-user credentials")
        self.user_id = user_id
        self.get_report_url = "https://netbroker.erstebroker.hu/netbroker/Logon.aspx"
        self.__SAVE_TO = Path(saveFolder)
        settings = get_settings()
        if (
            settings.selenium_downloads_dir is None
            or settings.local_downloads_dir is None
        ):
            raise RuntimeError(
                "SELENIUM_DOWNLOADS_DIR and LOCAL_DOWNLOADS_DIR must be configured"
            )
        self.__REMOTE_DIR = (
            Path(settings.selenium_downloads_dir).resolve() / self.__SAVE_TO.parts[-1]
        )
        self.__LOCAL_DIR = (
            Path(settings.local_downloads_dir).resolve() / self.__SAVE_TO.parts[-1]
        )
        logger.debug(
            "Initializing ErsteNetBroker for user_id=%s with save folder %s",
            user_id,
            self.__SAVE_TO,
        )
        logger.debug(
            "Remote download dir: %s, Local download dir: %s",
            self.__REMOTE_DIR,
            self.__LOCAL_DIR,
        )
        logger.debug("Config dir for credentials: %s", config_dir)
        self.driver: Optional[WebDriver] = None
        self.RESULT: Optional[str] = None

        creds = load_user_credentials(user_id=user_id, config_dir=config_dir)
        if not creds:
            raise RuntimeError(
                "ErsteNetBroker credentials not found for user. "
                "Save them via the secured FastAPI endpoint before using this class."
            )

        username = creds.get("username")
        account_num = creds.get("account_number")
        password = creds.get("password")

        if not (username and account_num and password):
            raise RuntimeError(
                "Incomplete credentials loaded for ErsteNetBroker for this user"
            )

        self.__USERNAME = str(username)
        self.__ACCOUNT_NUM = str(account_num)
        self.__PASSWORD = str(password)

        self._config_edge()

    def _require_driver(self) -> WebDriver:
        if self.driver is None:
            raise RuntimeError("WebDriver not initialized")
        return self.driver

    def __find_and_click(
        self, by: str = By.NAME, name: str = "", to_click: bool = True
    ) -> WebElement:
        driver = self._require_driver()
        logger.debug("Finding element by %s with name '%s'", by, name)
        if not name:
            logger.error("Element name is empty for find_and_click with by=%s", by)
            raise ValueError("Element name must not be empty")
        delay = 20
        try:
            logger.debug(
                "Waiting for presence of element by %s with name '%s'", by, name
            )
            my_elem = WebDriverWait(driver, delay).until(
                EC.presence_of_element_located((by, name))
            )
        except TimeoutException:
            logger.error("Timeout waiting for element by %s with name '%s'", by, name)
            raise AttributeError(f"Element not found: {name}")
        logger.debug("Element found: %s", my_elem)
        if to_click:
            logger.debug(
                "Waiting for element to be clickable by %s with name '%s'", by, name
            )
            ActionChains(driver).scroll_to_element(my_elem).move_to_element(
                my_elem
            ).perform()
            my_elem = WebDriverWait(driver, delay).until(
                EC.element_to_be_clickable((by, name))
            )
            my_elem.click()
        logger.debug("Element actions performed: %s", my_elem)
        return my_elem

    def __wait_for_page(self, timeout: int = 20) -> bool:
        logger.debug("Waiting for page to load with 'default.aspx' in URL")
        driver = self._require_driver()
        try:
            WebDriverWait(driver, timeout).until(
                lambda d: "default.aspx" in d.current_url
            )
            logger.debug("'default.aspx' found in URL: %s", driver.current_url)
            return True
        except TimeoutException:
            logger.warning(
                "Timeout waiting for 'default.aspx' in URL. Current URL: %s",
                driver.current_url,
            )
            return False

    def _file_exist_today(self) -> bool:
        files = get_all_files_from_folder(str(self.__SAVE_TO), "xls")
        for file in files:
            date = extract_date_from_filename(file)
            if date and is_today_in(date):
                logger.info("Found existing report file for today: %s", file)
                self.RESULT = file
                return True
        logger.debug("No existing report file found for today in %s", self.__SAVE_TO)
        return False

    def _config_edge(self) -> None:
        edge_options = Options()
        edge_options.add_argument("--headless=new")
        edge_options.add_argument("--remote-allow-origins=*")
        edge_options.add_argument("--disable-gpu")
        edge_options.add_argument("--window-size=1920,1080")
        edge_options.add_argument("--no-first-run")
        edge_options.add_argument("--log-level=3")
        edge_options.add_argument("--disable-blink-features=AutomationControlled")
        edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        edge_options.add_experimental_option("useAutomationExtension", False)
        edge_options.add_argument("--disable-dev-shm-usage")
        edge_options.add_experimental_option(
            "prefs",
            {
                "download.default_directory": str(
                    self.__REMOTE_DIR.resolve().absolute()
                ),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": False,
                "profile.default_content_settings.popups": 0,
                "profile.default_content_setting_values.automatic_downloads": 1,
            },
        )

        def ensure_directory(path: Path) -> None:
            try:
                os.makedirs(path, exist_ok=True)
                try:
                    os.chmod(path, 0o777)
                except Exception:
                    logger.warning("chmod not supported for %s", path)
            except Exception:
                logger.exception("Failed to create save folder %s", path)
                raise

        ensure_directory(self.__SAVE_TO)
        ensure_directory(self.__LOCAL_DIR)

        try:
            self.driver = webdriver.Remote(
                options=edge_options, command_executor="http://selenium:4444"
            )
            logger.debug("Edge WebDriver started")
        except WebDriverException:
            logger.exception(
                "Failed to start Edge WebDriver. Ensure browser and driver are installed and available in the container"
            )
            raise

    def _renameDownloadedFile(self, timeout: int = 180) -> str:
        download_folder = str(self.__LOCAL_DIR)
        end_time = time.time() + timeout
        has_timeout = True
        latest_file: Optional[Path] = None
        while time.time() < end_time:
            cr_files = glob.glob(os.path.join(download_folder, "*.crdownload"))
            if cr_files:
                logger.debug("Download in progress: %s", cr_files)
                time.sleep(1)
                continue

            files = glob.glob(os.path.join(download_folder, "*.xls*"))
            if files:
                latest_file = Path(max(files, key=os.path.getctime))
                logger.info("Download finished: %s", latest_file)
                has_timeout = False
                break
            time.sleep(1)

        if has_timeout or latest_file is None:
            raise TimeoutError(
                f"No downloaded file appeared in {download_folder} within {timeout} seconds"
            )

        import shutil

        newFileName = f'Riport_{datetime.now().strftime("%Y%m%d_%H%M")}.xls'
        new_path = self.__SAVE_TO / newFileName
        shutil.move(latest_file, new_path)
        self.RESULT = newFileName
        return newFileName

    def _handle_already_logged_in_Selenium(self) -> bool:
        logger.info("Already logged in on another session. Attempting to resolve...")
        driver = self._require_driver()
        try:
            self.__find_and_click(By.NAME, "ctl18$Button1")
            if "alreadyloggedin" in driver.current_url.lower():
                logger.info("Transaction code page reached; user must supply code")
                return True
            else:
                logger.error(
                    "Did not reach transaction code page after resolving 'already logged in'"
                )
                return False
        except Exception:
            logger.exception("Error while handling already-logged-in page")
            return False or "checksession" in driver.current_url.lower()

    def _handle_otp_Selenium(self, timestamp: int) -> bool:
        logger.info(
            "Two-factor authentication required; checking for OTP messages since ts=%s",
            timestamp,
        )
        otp_code = self._checkForCode(timestamp)
        logger.debug("OTP code retrieved: %s", "REDACTED" if otp_code else "None")
        if otp_code is None:
            logger.warning("OTP code not retrieved for timestamp %s", timestamp)
            return False

        try:
            otp_input = self.__find_and_click(By.NAME, "ctl17$txtSMS", False)
            otp_input.send_keys(otp_code)
            self.__find_and_click(By.NAME, "ctl17$btnGo")
            logger.debug("Submitted OTP code, waiting for landing page")
            logger.debug(
                "Current URL after submitting OTP: %s",
                self._require_driver().current_url,
            )
            if self.__wait_for_page(timeout=30):
                logger.info("get_report flow: OTP accepted and landing page reached")
                return True
            else:
                logger.warning(
                    "get_report flow: OTP may be incorrect or session expired"
                )
                return False
        except Exception:
            logger.exception("Exception while submitting OTP")
            return False

    def _handle_prev_session(self, timestamp: int) -> bool:
        no_error = self._handle_already_logged_in_Selenium()

        if no_error:
            no_error = self._handle_otp_Selenium(timestamp)

        return no_error

    def get_report(self) -> Optional[str]:
        self.RESULT = None
        if self._file_exist_today():
            logger.info("Report for today already exists: %s", self.RESULT)
            return self.RESULT

        timestamp = int((datetime.now().timestamp() - 60) * 1e3)

        try:
            driver = self._require_driver()
            driver.get(self.get_report_url)

            self.__find_and_click(By.NAME, "ctl04$un", to_click=False).send_keys(
                self.__USERNAME
            )
            self.__find_and_click(By.NAME, "ctl04$uk", to_click=False).send_keys(
                self.__ACCOUNT_NUM
            )
            self.__find_and_click(By.NAME, "ctl04$pw", to_click=False).send_keys(
                self.__PASSWORD
            )

            self.__find_and_click(By.NAME, "ctl04$btnLogon")

            no_error = self._handle_prev_session(timestamp=timestamp)

            if not no_error:
                logger.warning("Login/get_report aborted for user (no_error==False)")
                return None

            self.download_report()
            result_name = self._renameDownloadedFile()
            logger.info("Report downloaded and renamed to %s", result_name)
            try:
                formatter = reportFormatter(
                    fileName=result_name, fileLoc=str(self.__SAVE_TO)
                )
                formatter.save(True)
            except Exception:
                logger.exception("Failed to format/save report for %s", result_name)
            return result_name
        except Exception:
            logger.exception("Exception during get_report execution")
            return None
        finally:
            try:
                if self.driver:
                    self.driver.quit()
                    logger.debug("WebDriver quit")
            except Exception:
                logger.exception("Exception while quitting WebDriver")

    def download_report(self) -> None:
        self.__find_and_click(
            By.XPATH,
            "//td[@class='menuitem']/a/div[@class='menuitemtext' and text()='Riportok']",
        )
        self.__find_and_click(
            By.XPATH, "//a[@class='ReportTreeNode' and text()='Riportok']"
        )
        self.__find_and_click(By.XPATH, "//a[text()='Készletinformációk']")
        self.__find_and_click(
            By.NAME, "ctl_Default$ContentCtl$ModuleCtl$btnExportExcel"
        )

    def _checkForCode(self, timeStamp: int) -> Optional[str]:
        try:
            fb = Firebase()
            db = fb.database()
            token = fb.get_user_token(self.user_id)
        except Exception:
            logger.exception("Failed to obtain Firebase singleton or database")
            return None

        if not token or not token.get("userId"):
            logger.warning("No active token in Firebase when checking for OTP")
            return None

        retry_times = 30
        while retry_times > 0:
            try:
                changed_doc = db.run_query(
                    "messages",
                    f'uid == {token["userId"]} AND timestamp >= {timeStamp}',
                    token=token,
                )
                if hasattr(changed_doc, "documents") and changed_doc.documents:
                    doc = changed_doc.documents[0]
                    data_fields = doc.data_fields or {}
                    ts_field = data_fields.get("timestamp")
                    if ts_field and ts_field > timeStamp:
                        code_value = data_fields.get("code")
                        try:
                            db.delete_document(f"messages/{doc.name}", token=token)
                        except Exception:
                            logger.debug("Failed to delete OTP document %s", doc.name)
                        logger.info("OTP code found for user %s", token.get("userId"))
                        return str(code_value) if code_value is not None else None
            except Exception:
                logger.debug("No OTP message yet or query failed; will retry")
            time.sleep(1.0)
            retry_times -= 1

        logger.debug("Timed out waiting for OTP code (timestamp=%s)", timeStamp)
        return None
