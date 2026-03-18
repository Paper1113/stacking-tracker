import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
from tenacity import retry, stop_after_attempt, wait_fixed
from utils.i18n import t, DATA_TTL, DEFAULT_PLAYERS

TIMEZONE = ZoneInfo("Asia/Hong_Kong")

def get_connection():
    """Establish and return the Google Sheets connection."""
    return st.connection("gsheets", type=GSheetsConnection)

@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
def _read_with_retry(conn, worksheet):
    return conn.read(worksheet=worksheet, ttl=DATA_TTL)

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
        
        # Build a filtered DataFrame excluding scratched (DNF) records
        valid_df = df[(df["Time"].notnull()) & (~df["IsScratch"])].copy()
    except Exception as e:
        st.error(t("err_read_fail", err=e))
        df = pd.DataFrame(columns=["Timestamp", "Name", "Mode", "Time", "IsScratch"])
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

def save_record_to_cloud(conn, timestamp_str, name, mode, time_val, is_scratch):
    """Save a single record directly to Google Sheets."""
    url = st.secrets.connections.gsheets.spreadsheet
    ws = conn.client._client.open_by_url(url).worksheet("Data")
    
    # Prefix safe_mode to prevent Google Sheets from auto-formatting '3-3-3' as dates
    safe_mode = f"'{mode}" if mode in ["3-3-3", "3-6-3"] else mode
    row_data = [timestamp_str, name, safe_mode, time_val, is_scratch]
    ws.append_row(row_data, table_range="A1", value_input_option="USER_ENTERED")

def sync_temp_logs_to_cloud(conn, temp_logs):
    """Sync an array of temp logs to Google Sheets using batch append_rows."""
    url = st.secrets.connections.gsheets.spreadsheet
    ws = conn.client._client.open_by_url(url).worksheet("Data")

    rows_data = [
        [log["Timestamp"], log["Name"], f"'{log['Mode']}" if log["Mode"] in ["3-3-3", "3-6-3"] else log["Mode"], log["Time"], log["IsScratch"]]
        for log in temp_logs
    ]
    ws.append_rows(rows_data, table_range="A1", value_input_option="USER_ENTERED")

def _find_row_index(ws, timestamp_str, name, mode):
    """Helper to find the 1-based row index for a specific record."""
    all_values = ws.get_all_values()
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

def update_record_in_cloud(conn, timestamp_str, name, mode, new_time_val, is_scratch):
    """Update a specific record in Google Sheets."""
    url = st.secrets.connections.gsheets.spreadsheet
    ws = conn.client._client.open_by_url(url).worksheet("Data")
    
    row_idx = _find_row_index(ws, timestamp_str, name, mode)
    if row_idx is None:
        raise ValueError(t("msg_record_not_found"))
        
    # Update time (col 4 / D) and IsScratch (col 5 / E)
    ws.update_cell(row_idx, 4, new_time_val)
    ws.update_cell(row_idx, 5, is_scratch)

def delete_record_from_cloud(conn, timestamp_str, name, mode):
    """Delete a specific record from Google Sheets."""
    url = st.secrets.connections.gsheets.spreadsheet
    ws = conn.client._client.open_by_url(url).worksheet("Data")
    
    row_idx = _find_row_index(ws, timestamp_str, name, mode)
    if row_idx is None:
        raise ValueError(t("msg_record_not_found"))
        
    ws.delete_rows(row_idx)

