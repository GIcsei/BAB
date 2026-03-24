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
    match = re.search(r"(\d{8})_\d{4,6}", base)
    logger.debug(
        "Regex match for date extraction: %s", match.group(1) if match else "None"
    )
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

    def _load(
        self, file_path: Optional[str] = None, override: bool = False
    ) -> pd.DataFrame:
        """
        Load Excel file into a DataFrame. If `file_path` is provided, it will be used; otherwise, it defaults to `FOLDER/fileName`.
        Note: Only '.XLS' files are supported for loading. For '.XLSX' files, ensure they are saved in the correct format to avoid loading issues.
        """
        full = file_path if file_path else os.path.join(self.FOLDER, self.fileName)
        try:
            data = pd.read_excel(full)
        except Exception:
            logger.exception("Failed to load excel file %s", full)
            raise
        if override:
            self.data = data
        return data

    def save(self, zipped: bool = False, as_merged: bool = False) -> None:
        strTime = datetime.now().strftime("%Y%m%d_%H%M%S")
        if not is_today_in(self.TIME_STAMP):
            strTime = self.TIME_STAMP.strftime("%Y%m%d_%H%M%S")
        try:
            if zipped:
                self.data.to_parquet(
                    os.path.join(self.FOLDER, f"innerValue_{strTime}.parquet")
                )
            else:
                self.data.to_excel(
                    os.path.join(self.FOLDER, f"innerValue_{strTime}.xlsx"), index=False
                )
        except Exception:
            logger.exception("Failed to save formatted data to %s", self.FOLDER)
            raise

        if as_merged:
            self.data.to_parquet(
                os.path.join(self.FOLDER, f"merged_{strTime}.parquet"), index=False
            )

    def merge_all(self, safe_mode: bool = True) -> bool:
        if self.FOLDER is None:
            logger.error("No folder specified for merging files")
            return False
        files = get_all_files_from_folder(self.FOLDER, "xls")

        if not files:
            logger.warning("No xls files found in folder %s", self.FOLDER)
            return False
        merged_data = []
        logger.info("Merging %d files from folder %s", len(files), self.FOLDER)
        for file in files:
            try:
                data = self._load(file_path=file)
                self._format(data=data)
                merged_data.append(data)
            except Exception:
                logger.exception("Failed to load file %s during merge", file)

        if not merged_data:
            logger.warning("No data loaded from files in folder %s", self.FOLDER)
            return False

        merged_earlier = glob.glob(os.path.join(self.FOLDER, "merged_*.parquet"))
        if merged_earlier:
            try:
                existing = pd.read_parquet(merged_earlier[0])
                merged_data.append(existing)
                logger.info("Included existing merged.parquet in merge")
            except Exception:
                logger.exception("Failed to load existing merged.parquet during merge")

        try:
            self.data = pd.concat(merged_data).drop_duplicates(ignore_index=True)
            logger.info("Successfully merged data from %d files", len(files))
        except Exception:
            logger.exception(
                "Failed to concatenate data from files in folder %s", self.FOLDER
            )
            return False

        clean_up_list = ["parquet", "pkl"]
        if not safe_mode:
            clean_up_list.append("xls")

        for ext in clean_up_list:
            self._clean_up(extension=ext)

        return True

    def __list_clean_up(self, files: List[str]) -> None:
        for file in files:
            try:
                os.remove(file)
                logger.debug("Deleted file %s during cleanup", file)
            except Exception:
                logger.exception("Failed to delete file %s during cleanup", file)

        logger.info(
            "Cleanup completed for %d files in folder %s", len(files), self.FOLDER
        )

    def _clean_up(self, extension: str = "parquet") -> None:
        if self.FOLDER is None:
            logger.error("No folder specified for cleanup")
            return
        files = get_all_files_from_folder(self.FOLDER, extension)
        if not files:
            logger.warning(
                "No files found in folder %s with extension %s for cleanup",
                self.FOLDER,
                extension,
            )
            return
        self.__list_clean_up(files)

    def _format(self, data: Optional[pd.DataFrame] = None) -> None:
        df = self.data if data is None else data
        self._remove_values(data=df)
        self.search_for_currency(data=df)
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

    def _remove_values(self, data: Optional[pd.DataFrame] = None) -> None:
        df = self.data if data is None else data
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

    def search_for_currency(self, data: Optional[pd.DataFrame] = None) -> None:
        currency_values = {"HUF", "USD", "EUR"}
        df = self.data if data is None else data
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
