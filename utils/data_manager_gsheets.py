import streamlit as st
from streamlit_gsheets import GSheetsConnection
from gspread import service_account_from_dict
from gspread.exceptions import APIError
from gspread.utils import rowcol_to_a1
import pandas as pd
from datetime import datetime
import uuid
from tenacity import RetryError, retry, stop_after_attempt, wait_fixed
from utils.app_config import DATA_TTL, DEFAULT_PLAYERS, TIMEZONE
from utils.i18n import t
from utils.records import (
    RECORD_ID_COL,
    RECORD_COLUMNS,
    normalize_records_dataframe,
    find_row_index,
)

BACKFILL_BATCH_SIZE = 100
_DATA_WORKSHEET_CACHE = {}

def get_connection():
    """Establish and return the Google Sheets connection."""
    return st.connection("gsheets", type=GSheetsConnection)

@retry(stop=stop_after_attempt(3), wait=wait_fixed(1), reraise=True)
def _read_with_retry(conn, worksheet):
    return conn.read(worksheet=worksheet, ttl=DATA_TTL)

@retry(stop=stop_after_attempt(3), wait=wait_fixed(1), reraise=True)
def _write_with_retry(operation, *args, **kwargs):
    return operation(*args, **kwargs)

def _missing_record_id_mask(df):
    if df is None or df.empty or RECORD_ID_COL not in df.columns:
        return pd.Series([True] * len(df), index=df.index) if df is not None else pd.Series(dtype=bool)

    record_ids = df[RECORD_ID_COL]
    return (
        record_ids.isna()
        | (record_ids.astype(str).str.strip() == "")
        | (record_ids.astype(str).str.lower() == "nan")
        | (record_ids.astype(str).str.lower() == "<na>")
    )


class RecordIdBackfillError(RuntimeError):
    def __init__(self, message, successful_record_ids):
        super().__init__(message)
        self.successful_record_ids = successful_record_ids


def _chunked(items, size):
    for start in range(0, len(items), size):
        yield items[start:start + size]


def _backfill_missing_record_ids(conn, row_ids):
    if not row_ids:
        return []

    ws = _get_data_worksheet(conn)
    record_id_col_idx = _ensure_record_id_header(ws)
    successful_record_ids = []
    for row_batch in _chunked(row_ids, BACKFILL_BATCH_SIZE):
        batch_payload = [
            {
                "range": rowcol_to_a1(row_idx, record_id_col_idx),
                "values": [[record_id]],
            }
            for row_idx, record_id in row_batch
        ]
        try:
            _write_with_retry(ws.batch_update, batch_payload, value_input_option="RAW")
        except Exception as exc:
            raise RecordIdBackfillError(_format_error(exc), successful_record_ids) from exc
        successful_record_ids.extend(row_batch)

    return successful_record_ids


def _format_error(exc):
    if isinstance(exc, RetryError):
        last_exc = exc.last_attempt.exception()
        if last_exc is not None:
            return _format_error(last_exc)
    if isinstance(exc, APIError):
        response = getattr(exc, "response", None)
        if response is not None:
            try:
                error = response.json().get("error", {})
                message = error.get("message")
                status = error.get("status")
                code = error.get("code")
                if message:
                    prefix = "Google Sheets API error"
                    details = " ".join(str(part) for part in (code, status) if part)
                    return f"{prefix} ({details}): {message}" if details else f"{prefix}: {message}"
            except ValueError:
                text = getattr(response, "text", "")
                if text:
                    return text
    return str(exc)

def format_cloud_error(exc):
    return _format_error(exc)

def _get_gsheets_service_account_config():
    """Read the configured gsheets service account config from Streamlit secrets."""
    try:
        raw_config = st.secrets.connections.gsheets
    except Exception as exc:
        raise RuntimeError("GSheets connection secrets are unavailable.") from exc

    config = raw_config.to_dict() if hasattr(raw_config, "to_dict") else dict(raw_config)
    spreadsheet_url = config.get("spreadsheet")
    if not spreadsheet_url:
        raise RuntimeError("GSheets spreadsheet URL is missing from secrets.")
    if config.get("type") != "service_account":
        raise RuntimeError("GSheets write operations require a service_account connection.")

    credentials = {k: v for k, v in config.items() if k not in {"spreadsheet", "worksheet"}}
    return spreadsheet_url, credentials

def _worksheet_cache_key_from_credentials(spreadsheet_url, credentials):
    return (
        "service-account",
        spreadsheet_url,
        credentials.get("client_email"),
        credentials.get("private_key_id"),
    )

def _get_data_worksheet_from_service_account_secrets():
    """Fallback worksheet lookup using raw service-account secrets."""
    spreadsheet_url, credentials = _get_gsheets_service_account_config()
    cache_key = _worksheet_cache_key_from_credentials(spreadsheet_url, credentials)
    if cache_key in _DATA_WORKSHEET_CACHE:
        return _DATA_WORKSHEET_CACHE[cache_key]

    client = service_account_from_dict(credentials)
    worksheet = client.open_by_url(spreadsheet_url).worksheet("Data")
    _DATA_WORKSHEET_CACHE[cache_key] = worksheet
    return worksheet

def _get_data_worksheet(conn):
    """Open the Data worksheet for write operations.

    Prefer the connection's authenticated client when it exposes worksheet
    selection, so existing st-gsheets-connection credential flows keep
    working. Fall back to raw service-account secrets only when needed.
    """
    client = getattr(conn, "client", None)
    # _select_worksheet is private in st-gsheets-connection but is the only
    # way to open a named worksheet via the connection client.  The hasattr
    # guard + fallback below protect against future API changes.
    if client is not None and hasattr(client, "_select_worksheet"):
        cache_key = ("connection-client", id(client), "Data")
        if cache_key not in _DATA_WORKSHEET_CACHE:
            _DATA_WORKSHEET_CACHE[cache_key] = client._select_worksheet(worksheet="Data")
        return _DATA_WORKSHEET_CACHE[cache_key]

    return _get_data_worksheet_from_service_account_secrets()

def load_data(conn):
    """
    Read data from the "Data" worksheet.
    Returns (df, valid_df).
    valid_df excludes scratched (Scratch) records and rows with invalid times.
    """
    try:
        raw_df = _read_with_retry(conn, "Data")
        missing_record_id_mask = _missing_record_id_mask(raw_df)
        df = normalize_records_dataframe(raw_df)

        generated_record_ids = {
            idx: str(uuid.uuid4())
            for idx in df.index[missing_record_id_mask]
        }
        if generated_record_ids:
            backfill_rows = [
                (int(idx) + 2, record_id)
                for idx, record_id in generated_record_ids.items()
            ]
            successful_backfills = []
            try:
                successful_backfills = _backfill_missing_record_ids(conn, backfill_rows)
            except RecordIdBackfillError as backfill_err:
                successful_backfills = backfill_err.successful_record_ids
                st.warning(f"RecordId backfill skipped: {backfill_err}")
            except Exception as backfill_err:
                st.warning(f"RecordId backfill skipped: {_format_error(backfill_err)}")

            for row_idx, record_id in successful_backfills:
                df_idx = row_idx - 2
                if df_idx in df.index:
                    df.loc[df_idx, RECORD_ID_COL] = record_id
        
        # Build a filtered DataFrame excluding scratched (Scratch) records
        valid_df = df[(df["Time"].notnull()) & (~df["IsScratch"])].copy()
    except Exception as e:
        st.error(t("err_read_fail", err=e))
        df = pd.DataFrame(columns=["Timestamp", "Name", "Mode", "Time", "IsScratch", RECORD_ID_COL])
        valid_df = df.copy()
        
    return df, valid_df

def load_players(conn, default_names_from_data):
    """
    Read player names from the "Players" worksheet.
    Falls back to names found in Data, or DEFAULT_PLAYERS.
    """
    try:
        players_df = _read_with_retry(conn, "Players")
        if "Name" in players_df.columns:
            names = players_df["Name"].dropna().astype(str).str.strip().tolist()
        else:
            col_name = str(players_df.columns[0]).strip()
            names = []
            if col_name and not col_name.startswith("Unnamed"):
                names.append(col_name)
            names.extend(players_df.iloc[:, 0].dropna().astype(str).str.strip().tolist())
    except Exception:
        names = default_names_from_data

    names = [n for n in names if n]
    if not names:
        names = DEFAULT_PLAYERS
        
    return names

def load_goals(conn):
    """
    Read goal settings from the "Goals" worksheet.
    """
    goals_df = pd.DataFrame(columns=["Name", "Mode", "TargetTime"])
    try:
        g_df = _read_with_retry(conn, "Goals")
        if not g_df.empty and {"Mode", "TargetTime"}.issubset(g_df.columns):
            if "Name" not in g_df.columns:
                g_df["Name"] = "All"
            g_df["Name"] = g_df["Name"].fillna("All").astype(str).str.strip()
            g_df["Mode"] = g_df["Mode"].astype(str).str.strip().str.lstrip("'")
            g_df["TargetTime"] = pd.to_numeric(g_df["TargetTime"], errors='coerce')
            goals_df = g_df.dropna(subset=["TargetTime"])
    except Exception:
        pass
        
    return goals_df

def get_current_timestamp():
    """Return the current timestamp string."""
    return datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")

def _ensure_record_id_header_with_headers(ws):
    """Ensure the Data worksheet has a RecordId header column."""
    headers = _write_with_retry(ws.row_values, 1)
    if RECORD_ID_COL in headers:
        return headers.index(RECORD_ID_COL) + 1, headers

    record_id_col_idx = max(len(headers) + 1, 6)
    _write_with_retry(ws.update_cell, 1, record_id_col_idx, RECORD_ID_COL)
    updated_headers = list(headers)
    while len(updated_headers) < record_id_col_idx:
        updated_headers.append("")
    updated_headers[record_id_col_idx - 1] = RECORD_ID_COL
    return record_id_col_idx, updated_headers

def _ensure_record_id_header(ws):
    record_id_col_idx, _headers = _ensure_record_id_header_with_headers(ws)
    return record_id_col_idx

def _build_record_row(headers, timestamp_str, name, mode, time_val, is_scratch, record_id):
    values_by_header = {
        "Timestamp": timestamp_str,
        "Name": name,
        "Mode": f"'{mode}" if mode in ["3-3-3", "3-6-3"] else mode,
        "Time": time_val,
        "IsScratch": is_scratch,
        RECORD_ID_COL: record_id,
    }
    width = max(len(headers), len(RECORD_COLUMNS))
    row_data = [""] * width

    for idx, header in enumerate(headers):
        if header in values_by_header:
            row_data[idx] = values_by_header[header]

    for idx, column in enumerate(RECORD_COLUMNS):
        if column not in headers and idx < width:
            row_data[idx] = values_by_header[column]

    return row_data

def save_record_to_cloud(conn, timestamp_str, name, mode, time_val, is_scratch, record_id=None):
    """Save a single record directly to Google Sheets."""
    ws = _get_data_worksheet(conn)
    _record_id_col_idx, headers = _ensure_record_id_header_with_headers(ws)
    if not record_id:
        record_id = str(uuid.uuid4())
    
    row_data = _build_record_row(headers, timestamp_str, name, mode, time_val, is_scratch, record_id)
    _write_with_retry(ws.append_row, row_data, table_range="A1", value_input_option="USER_ENTERED")
    return record_id

def sync_temp_logs_to_cloud(conn, temp_logs):
    """Sync an array of temp logs to Google Sheets using batch append_rows."""
    ws = _get_data_worksheet(conn)
    _record_id_col_idx, headers = _ensure_record_id_header_with_headers(ws)

    rows_data = [
        _build_record_row(
            headers,
            log["Timestamp"],
            log["Name"],
            log["Mode"],
            log["Time"],
            log["IsScratch"],
            log.get(RECORD_ID_COL) or str(uuid.uuid4())
        )
        for log in temp_logs
    ]
    _write_with_retry(ws.append_rows, rows_data, table_range="A1", value_input_option="USER_ENTERED")

def _find_row_index(ws, timestamp_str=None, name=None, mode=None, record_id=None):
    """Helper to find the 1-based row index for a specific record."""
    all_values = _write_with_retry(ws.get_all_values)
    return find_row_index(all_values, timestamp_str, name, mode, record_id)

def update_record_in_cloud(conn, timestamp_str, name, mode, new_time_val, is_scratch, record_id=None):
    """Update a specific record in Google Sheets."""
    ws = _get_data_worksheet(conn)
    
    row_idx = _find_row_index(ws, timestamp_str, name, mode, record_id)
    if row_idx is None:
        raise ValueError(t("msg_record_not_found"))
        
    _write_with_retry(
        ws.update,
        f"D{row_idx}:E{row_idx}",
        [[new_time_val, is_scratch]],
        value_input_option="USER_ENTERED",
    )

def delete_record_from_cloud(conn, timestamp_str, name, mode, record_id=None):
    """Delete a specific record from Google Sheets."""
    ws = _get_data_worksheet(conn)
    
    row_idx = _find_row_index(ws, timestamp_str, name, mode, record_id)
    if row_idx is None:
        raise ValueError(t("msg_record_not_found"))
        
    _write_with_retry(ws.delete_rows, row_idx)
