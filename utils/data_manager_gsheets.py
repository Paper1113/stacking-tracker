import streamlit as st
from streamlit_gsheets import GSheetsConnection
from gspread import service_account_from_dict
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import uuid
from tenacity import retry, stop_after_attempt, wait_fixed
from utils.i18n import t, DATA_TTL, DEFAULT_PLAYERS

TIMEZONE = ZoneInfo("Asia/Hong_Kong")
RECORD_ID_COL = "RecordId"
LEGACY_ROW_PREFIX = "legacy-row-"

def get_connection():
    """Establish and return the Google Sheets connection."""
    return st.connection("gsheets", type=GSheetsConnection)

@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
def _read_with_retry(conn, worksheet):
    return conn.read(worksheet=worksheet, ttl=DATA_TTL)

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

def _get_data_worksheet_from_service_account_secrets():
    """Fallback worksheet lookup using raw service-account secrets."""
    spreadsheet_url, credentials = _get_gsheets_service_account_config()
    client = service_account_from_dict(credentials)
    return client.open_by_url(spreadsheet_url).worksheet("Data")

def _get_data_worksheet(conn):
    """Open the Data worksheet for write operations.

    Prefer the connection's authenticated client when it exposes worksheet
    selection, so existing st-gsheets-connection credential flows keep
    working. Fall back to raw service-account secrets only when needed.
    """
    client = getattr(conn, "client", None)
    if client is not None and hasattr(client, "_select_worksheet"):
        return client._select_worksheet(worksheet="Data")

    return _get_data_worksheet_from_service_account_secrets()

def load_data(conn):
    """
    Read data from the "Data" worksheet.
    Returns (df, valid_df).
    valid_df excludes scratched (DNF) records and rows with invalid times.
    """
    try:
        df = _read_with_retry(conn, "Data")

        # Strip leading single quotes from Mode
        if "Mode" in df.columns:
            df["Mode"] = df["Mode"].astype(str).str.lstrip("'")
            
        # Ensure IsScratch column is boolean
        if "IsScratch" in df.columns:
            df["IsScratch"] = df["IsScratch"].astype(str).str.upper() == "TRUE"
        else:
            df["IsScratch"] = False

        # Coerce Time column to numeric for calculations
        df["Time"] = pd.to_numeric(df["Time"], errors='coerce')

        # Ensure RecordId exists for robust update/delete targeting.
        # For legacy rows without RecordId in the sheet, generate row-based fallback ID in memory.
        if RECORD_ID_COL not in df.columns:
            df[RECORD_ID_COL] = [f"{LEGACY_ROW_PREFIX}{i + 2}" for i in range(len(df))]
        else:
            missing_mask = (
                df[RECORD_ID_COL].isna()
                | (df[RECORD_ID_COL].astype(str).str.strip() == "")
                | (df[RECORD_ID_COL].astype(str).str.lower() == "nan")
            )
            df.loc[missing_mask, RECORD_ID_COL] = [
                f"{LEGACY_ROW_PREFIX}{i + 2}" for i in df.index[missing_mask]
            ]
            df[RECORD_ID_COL] = df[RECORD_ID_COL].astype(str)
        
        # Build a filtered DataFrame excluding scratched (DNF) records
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

def _ensure_record_id_header(ws):
    """Ensure the Data worksheet has a RecordId header column."""
    headers = ws.row_values(1)
    if RECORD_ID_COL in headers:
        return headers.index(RECORD_ID_COL) + 1

    record_id_col_idx = max(len(headers) + 1, 6)
    ws.update_cell(1, record_id_col_idx, RECORD_ID_COL)
    return record_id_col_idx

def save_record_to_cloud(conn, timestamp_str, name, mode, time_val, is_scratch, record_id=None):
    """Save a single record directly to Google Sheets."""
    ws = _get_data_worksheet(conn)
    _ensure_record_id_header(ws)
    if not record_id:
        record_id = str(uuid.uuid4())
    
    # Prefix safe_mode to prevent Google Sheets from auto-formatting '3-3-3' as dates
    safe_mode = f"'{mode}" if mode in ["3-3-3", "3-6-3"] else mode
    row_data = [timestamp_str, name, safe_mode, time_val, is_scratch, record_id]
    ws.append_row(row_data, table_range="A1", value_input_option="USER_ENTERED")
    return record_id

def sync_temp_logs_to_cloud(conn, temp_logs):
    """Sync an array of temp logs to Google Sheets using batch append_rows."""
    ws = _get_data_worksheet(conn)
    _ensure_record_id_header(ws)

    rows_data = [
        [
            log["Timestamp"],
            log["Name"],
            f"'{log['Mode']}" if log["Mode"] in ["3-3-3", "3-6-3"] else log["Mode"],
            log["Time"],
            log["IsScratch"],
            log.get(RECORD_ID_COL) or str(uuid.uuid4())
        ]
        for log in temp_logs
    ]
    ws.append_rows(rows_data, table_range="A1", value_input_option="USER_ENTERED")

def _find_row_index(ws, timestamp_str=None, name=None, mode=None, record_id=None):
    """Helper to find the 1-based row index for a specific record."""
    all_values = ws.get_all_values()
    if not all_values:
        return None

    headers = all_values[0]
    record_id_col_idx = headers.index(RECORD_ID_COL) if RECORD_ID_COL in headers else None

    if record_id:
        if record_id.startswith(LEGACY_ROW_PREFIX):
            try:
                legacy_row_idx = int(record_id.replace(LEGACY_ROW_PREFIX, "", 1))
                if 2 <= legacy_row_idx <= len(all_values):
                    if timestamp_str is None and name is None and mode is None:
                        return legacy_row_idx
                    row = all_values[legacy_row_idx - 1]
                    if len(row) >= 3:
                        r_ts, r_name, r_mode = row[0], row[1], row[2].lstrip("'")
                        if r_ts == timestamp_str and r_name == name and r_mode == mode:
                            return legacy_row_idx
            except ValueError:
                pass

        if record_id_col_idx is not None:
            for i, row in enumerate(all_values):
                if i == 0:
                    continue
                if len(row) > record_id_col_idx and row[record_id_col_idx] == record_id:
                    return i + 1

    # Headers are usually at row 1 (index 0 in list). Find the match.
    # We strip single quotes from Mode just in case.
    for i, row in enumerate(all_values):
        if i == 0:
            continue # skip header
        if len(row) >= 3:
            r_ts, r_name, r_mode = row[0], row[1], row[2].lstrip("'")
            if r_ts == timestamp_str and r_name == name and r_mode == mode:
                # GSheets rows are 1-indexed
                return i + 1
    return None

def update_record_in_cloud(conn, timestamp_str, name, mode, new_time_val, is_scratch, record_id=None):
    """Update a specific record in Google Sheets."""
    ws = _get_data_worksheet(conn)
    
    row_idx = _find_row_index(ws, timestamp_str, name, mode, record_id)
    if row_idx is None:
        raise ValueError(t("msg_record_not_found"))
        
    # Update time (col 4 / D) and IsScratch (col 5 / E)
    ws.update_cell(row_idx, 4, new_time_val)
    ws.update_cell(row_idx, 5, is_scratch)

def delete_record_from_cloud(conn, timestamp_str, name, mode, record_id=None):
    """Delete a specific record from Google Sheets."""
    ws = _get_data_worksheet(conn)
    
    row_idx = _find_row_index(ws, timestamp_str, name, mode, record_id)
    if row_idx is None:
        raise ValueError(t("msg_record_not_found"))
        
    ws.delete_rows(row_idx)
