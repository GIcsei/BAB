import glob
import logging
import os
import re
from datetime import date, datetime
from os import path
from typing import List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def is_today_in(date_obj: date) -> bool:
    return date_obj == datetime.today().date()


def extract_date_from_filename(filename: str) -> Optional[date]:
    """
    Extract a date (YYYYMMDD) from a filename that contains pattern YYYYMMDD_HHMM.
    Returns a datetime.date or None.
    """
    base = path.basename(filename)
    logger.debug("Extracting date from filename: %s", base)
    match = re.search(r"(\d{8})_\d{4}", base)
    logger.debug("Regex match for date extraction: %s", match.group(1) if match else "None")
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y%m%d").date()
        except Exception:
            logger.debug("Failed to parse date from filename: %s", filename)
            return None
    return None


def get_all_files_from_folder(folder: Optional[str], extension: str) -> List[str]:
    """
    Return list of files (full paths) in `folder` matching `*.{extension}`.
    """
    if not folder:
        return []
    dir_to_check = path.join(path.abspath(folder), f"*.{extension}")
    try:
        files = glob.glob(dir_to_check)
    except Exception:
        logger.exception("Error while globbing %s", dir_to_check)
        return []
    logger.debug("Found %d files for pattern %s", len(files), dir_to_check)
    return files


class reportFormatter:
    """Class to load, format, and save netbank report data from Excel files."""
    FOLDER = r"D:\Erste"
    fileName = r"Riport.xlsx"
    COLUMNS = (
        "Instrumentum",
        "V/E",
        "Készletnap",
        "Darabszám",
        "Beker. ár",
        "Bek. árfolyamérték",
        "Bek. költség",
        "Piaci ár",
        "P&L/db HUF",
        "Bruttó P&L HUF",
        "Nettó P&L HUF",
        "Hozam %",
        "Készletcsoport",
        "Készlet ÜK",
        "Árfolyam",
    )
    TIME_STAMP = date.today()

    def __init__(self, fileName: Optional[str] = None, fileLoc: Optional[str] = None):
        if fileLoc is not None:
            self.FOLDER = fileLoc
        if fileName is not None:
            self.fileName = fileName
            extracted = extract_date_from_filename(self.fileName)
            self.TIME_STAMP = extracted if extracted is not None else date.today()
        self.data: pd.DataFrame = self._load()
        self._format()

    def _load(self) -> pd.DataFrame:
        full = os.path.join(self.FOLDER, self.fileName)
        try:
            self.data = pd.read_excel(full)
        except Exception:
            logger.exception("Failed to load excel file %s", full)
            raise
        return self.data

    def save(self, zipped: bool = False) -> None:
        strTime = datetime.now().strftime("%Y%m%d_%H%M")
        if not is_today_in(self.TIME_STAMP):
            strTime = self.TIME_STAMP.strftime("%Y%m%d_%H%M")
        try:
            if zipped:
                self.data.to_pickle(
                    os.path.join(self.FOLDER, f"innerValue_{strTime}.pkl")
                )
            else:
                self.data.to_excel(
                    os.path.join(self.FOLDER, f"innerValue_{strTime}.xlsx"), index=False
                )
        except Exception:
            logger.exception("Failed to save formatted data to %s", self.FOLDER)
            raise

    def _format(self) -> None:
        df = self.data
        self._remove_values()
        self.search_for_currency()
        try:
            df.columns = self.COLUMNS
        except Exception:
            logger.warning(
                "Column count mismatch while assigning COLUMNS; keeping original columns"
            )
        df.reset_index(inplace=True, drop=True)
        df["Date_of_import"] = self.TIME_STAMP
        try:
            logger.debug("Formatted data preview:\n%s", df.head().to_string())
        except Exception:
            logger.debug("Formatted data available")

    def _remove_values(self) -> None:
        df = self.data
        try:
            df.drop(df.tail(1).index, inplace=True)
        except Exception:
            logger.debug("Failed to drop tail row - possibly empty dataframe")
        try:
            df.drop(df.head(6).index, inplace=True)
        except Exception:
            logger.debug("Failed to drop head rows - possibly smaller dataframe")
        df.dropna(axis=1, how="all", inplace=True)
        if df.shape[1] > 0:
            df.dropna(subset=[df.columns[0]], inplace=True)
        if df.shape[1] > 1:
            df.dropna(subset=df.columns[1:], inplace=True)

    def search_for_currency(self) -> None:
        currency_values = {"HUF", "USD", "EUR"}
        df = self.data
        try:
            cols_to_drop = [
                col
                for col in df.columns
                if df[col].dropna().isin(currency_values).all()
            ]
        except Exception:
            cols_to_drop = []
        if len(cols_to_drop) == 0:
            return
        try:
            df["NewCurrency"] = df[cols_to_drop[0]]
            df.drop(columns=cols_to_drop, inplace=True)
        except Exception:
            logger.exception("Failed while extracting currency columns")
