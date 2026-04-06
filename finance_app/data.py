from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import gspread
import pandas as pd
import streamlit as st
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from google.oauth2.service_account import Credentials

from finance_app.config import DATASETS, DATA_DIR


def ensure_local_files() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    for config in DATASETS.values():
        path = Path(config["path"])
        if not path.exists():
            pd.DataFrame(columns=config["columns"]).to_csv(path, index=False)


def normalize_dataframe(df: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
    config = DATASETS[dataset_name]
    data = df.copy()
    for column in config["columns"]:
        if column not in data.columns:
            data[column] = pd.Series(dtype="object")
    data = data[config["columns"]]
    for column in config.get("date_columns", []):
        data[column] = pd.to_datetime(data[column], errors="coerce")
    for column in config.get("numeric_columns", []):
        data[column] = pd.to_numeric(data[column], errors="coerce").fillna(0.0)
    return data


def serialize_dataframe(df: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
    config = DATASETS[dataset_name]
    data = df.copy()
    for column in config.get("date_columns", []):
        if column in data.columns:
            data[column] = pd.to_datetime(data[column], errors="coerce").dt.strftime("%Y-%m-%d")
    return data[config["columns"]]


def _gsheets_secrets() -> dict:
    try:
        secrets = dict(st.secrets["connections"]["gsheets"])
    except Exception:
        return {}
    return secrets


def get_data_mode() -> str:
    return "gsheets" if st.sidebar.toggle("Usar Google Sheets", value=False) else "local"


@st.cache_resource(show_spinner=False)
def get_gspread_client(secrets: dict):
    if not secrets:
        return None
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(secrets, scopes=scopes)
    return gspread.authorize(creds)


@dataclass
class DataStore:
    mode: str
    client: Optional[object] = None
    spreadsheet_url: Optional[str] = None

    @classmethod
    def build(cls) -> "DataStore":
        ensure_local_files()
        mode = get_data_mode()
        if mode == "local":
            return cls(mode="local")

        secrets = _gsheets_secrets().copy()
        spreadsheet_url = secrets.pop("spreadsheet", None)
        if not secrets or not spreadsheet_url:
            st.sidebar.warning("Google Sheets nao configurado. Usando base local.")
            return cls(mode="local")

        try:
            client = get_gspread_client(secrets)
            return cls(mode="gsheets", client=client, spreadsheet_url=spreadsheet_url)
        except Exception as exc:
            st.sidebar.warning(f"Falha ao autenticar no Google Sheets: {exc}")
            return cls(mode="local")

    def _worksheet(self, dataset_name: str):
        if self.client is None or self.spreadsheet_url is None:
            raise RuntimeError("Google Sheets nao configurado.")
        spreadsheet = self.client.open_by_url(self.spreadsheet_url)
        title = DATASETS[dataset_name]["worksheet"]
        try:
            return spreadsheet.worksheet(title)
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=title, rows=1000, cols=max(6, len(DATASETS[dataset_name]["columns"])))
            worksheet.update([DATASETS[dataset_name]["columns"]])
            return worksheet

    def read(self, dataset_name: str) -> pd.DataFrame:
        if self.mode == "local":
            df = pd.read_csv(DATASETS[dataset_name]["path"])
            return normalize_dataframe(df, dataset_name)

        worksheet = self._worksheet(dataset_name)
        df = get_as_dataframe(worksheet, evaluate_formulas=True, header=0).dropna(how="all")
        return normalize_dataframe(df, dataset_name)

    def write(self, dataset_name: str, df: pd.DataFrame) -> None:
        serialized = serialize_dataframe(df, dataset_name)
        if self.mode == "local":
            serialized.to_csv(DATASETS[dataset_name]["path"], index=False)
            return

        worksheet = self._worksheet(dataset_name)
        worksheet.clear()
        set_with_dataframe(worksheet, serialized, include_index=False, include_column_header=True, resize=True)

    def append(self, dataset_name: str, row: dict) -> None:
        current = self.read(dataset_name)
        updated = pd.concat([current, pd.DataFrame([row])], ignore_index=True)
        self.write(dataset_name, updated)


def load_all_data(store: DataStore) -> dict[str, pd.DataFrame]:
    return {name: store.read(name) for name in DATASETS}
