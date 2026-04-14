import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import uuid
from tenacity import retry, stop_after_attempt, wait_fixed
from utils.i18n import t, DATA_TTL, DEFAULT_PLAYERS
from utils.firestore_manager import get_firestore_client
from google.cloud.firestore_v1.base_query import FieldFilter

TIMEZONE = ZoneInfo("Asia/Hong_Kong")
RECORD_ID_COL = "RecordId"
FIRESTORE_BATCH_LIMIT = 499

def get_connection():
    """Return the Firestore client. Name kept for compatibility."""
    return get_firestore_client()

@st.cache_data(ttl=DATA_TTL, show_spinner=False)
@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
def load_data(_conn):
    # Leading underscore prevents st.cache_data from hashing the connection object.
    conn = _conn
    """
    Read data from the 'records' Firestore collection.
    Returns (df, valid_df).
    valid_df excludes scratched (DNF) records and rows with invalid times.
    """
    # Streamlit caching based on Firestore might require different approach, 
    # but we will just query Firestore and cache it if st.cache_data is managing this at higher level, 
    # wait, the original didn't use st.cache_data here, it used gsheets ttl.
    # To avoid constant reads, maybe wrap this in st.cache_data in production, but leaving it clean for now.
    
    try:
        docs = conn.collection("records").stream()
        records = []
        for doc in docs:
            data = doc.to_dict()
            records.append(data)
            
        df = pd.DataFrame(records)
        
        if df.empty:
            df = pd.DataFrame(columns=["Timestamp", "Name", "Mode", "Time", "IsScratch", RECORD_ID_COL])
            
        # Strip leading single quotes from Mode
        if "Mode" in df.columns:
            df["Mode"] = df["Mode"].astype(str).str.lstrip("'")
            
        # Ensure IsScratch column is boolean
        if "IsScratch" in df.columns:
            # Firestore handles bools natively, but just in case
            df["IsScratch"] = df["IsScratch"].fillna(False).astype(bool)
        else:
            df["IsScratch"] = False

        # Coerce Time column to numeric for calculations
        if "Time" in df.columns:
            df["Time"] = pd.to_numeric(df["Time"], errors='coerce')
        else:
            df["Time"] = pd.Series(dtype=float)

        # Ensure RecordId exists for robust update/delete targeting.
        if RECORD_ID_COL not in df.columns:
            df[RECORD_ID_COL] = [str(uuid.uuid4()) for _ in range(len(df))]
        else:
            missing_mask = (
                df[RECORD_ID_COL].isna()
                | (df[RECORD_ID_COL].astype(str).str.strip() == "")
                | (df[RECORD_ID_COL].astype(str).str.lower() == "nan")
            )
            df.loc[missing_mask, RECORD_ID_COL] = [
                str(uuid.uuid4()) for _ in range(missing_mask.sum())
            ]
            df[RECORD_ID_COL] = df[RECORD_ID_COL].astype(str)
        
        # Build a filtered DataFrame excluding scratched (DNF) records
        valid_df = df[(df["Time"].notnull()) & (~df["IsScratch"])].copy()
    except Exception as e:
        st.error(t("err_read_fail", err=e))
        df = pd.DataFrame(columns=["Timestamp", "Name", "Mode", "Time", "IsScratch", RECORD_ID_COL])
        valid_df = df.copy()
        
    return df, valid_df

@st.cache_data(ttl=DATA_TTL, show_spinner=False)
@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
def load_players(_conn, default_names_from_data):
    # Leading underscore prevents st.cache_data from hashing the connection object.
    conn = _conn
    """
    Read player names from the 'players' Firestore collection.
    Falls back to names found in Data, or DEFAULT_PLAYERS.
    """
    names = []
    try:
        docs = conn.collection("players").stream()
        for doc in docs:
            names.append(doc.to_dict().get("Name", doc.id))
    except Exception:
        pass

    if not names:
        names = default_names_from_data

    names = [n for n in names if n]
    if not names:
        names = DEFAULT_PLAYERS
        
    # Sort names alphabetically for consistency
    return sorted(names)

@st.cache_data(ttl=DATA_TTL, show_spinner=False)
@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
def load_goals(_conn):
    # Leading underscore prevents st.cache_data from hashing the connection object.
    conn = _conn
    """
    Read goal settings from the 'goals' Firestore collection.
    """
    goals_data = []
    try:
        docs = conn.collection("goals").stream()
        for doc in docs:
            goals_data.append(doc.to_dict())
    except Exception:
        pass

    df = pd.DataFrame(goals_data)
    if df.empty:
        return pd.DataFrame(columns=["Name", "Mode", "TargetTime"])
        
    if "Name" not in df.columns:
        df["Name"] = "All"
    df["Name"] = df["Name"].fillna("All").astype(str).str.strip()
    
    if "Mode" in df.columns:
        df["Mode"] = df["Mode"].astype(str).str.strip().str.lstrip("'")
        
    if "TargetTime" in df.columns:
        df["TargetTime"] = pd.to_numeric(df["TargetTime"], errors='coerce')
        df = df.dropna(subset=["TargetTime"])
        
    return df

def get_current_timestamp():
    """Return the current timestamp string."""
    return datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")

def save_record_to_cloud(conn, timestamp_str, name, mode, time_val, is_scratch, record_id=None):
    """Save a single record directly to Firestore."""
    if not record_id:
        record_id = str(uuid.uuid4())
    
    doc_ref = conn.collection("records").document(str(record_id))
    doc_ref.set({
        "Timestamp": timestamp_str,
        "Name": name,
        "Mode": mode,
        "Time": time_val,
        "IsScratch": bool(is_scratch),
        RECORD_ID_COL: str(record_id)
    })
    return record_id

def sync_temp_logs_to_cloud(conn, temp_logs):
    """Sync an array of temp logs to Firestore using batch writes."""
    for start in range(0, len(temp_logs), FIRESTORE_BATCH_LIMIT):
        batch = conn.batch()
        chunk = temp_logs[start:start + FIRESTORE_BATCH_LIMIT]

        for log in chunk:
            rec_id = log.get(RECORD_ID_COL) or str(uuid.uuid4())
            doc_ref = conn.collection("records").document(str(rec_id))

            batch.set(doc_ref, {
                "Timestamp": log["Timestamp"],
                "Name": log["Name"],
                "Mode": log["Mode"],
                "Time": log["Time"],
                "IsScratch": bool(log.get("IsScratch", False)),
                RECORD_ID_COL: str(rec_id)
            })

        batch.commit()

def _find_document_id(conn, timestamp_str, name, mode, record_id=None):
    """Helper to find the Firestore document ID for a record."""
    if record_id:
        doc_ref = conn.collection("records").document(str(record_id))
        if doc_ref.get().exists:
            return str(record_id)
            
    # Fallback: query by exact match
    # Since Mode might be stored differently, we check for match
    query = conn.collection("records").where(filter=FieldFilter("Timestamp", "==", timestamp_str)) \
                                     .where(filter=FieldFilter("Name", "==", name))
    
    docs = query.stream()
    for doc in docs:
        d_mode = doc.to_dict().get("Mode", "").lstrip("'")
        if d_mode == mode.lstrip("'"):
            return doc.id
            
    return None

def update_record_in_cloud(conn, timestamp_str, name, mode, new_time_val, is_scratch, record_id=None):
    """Update a specific record in Firestore."""
    doc_id = _find_document_id(conn, timestamp_str, name, mode, record_id)
    if not doc_id:
        raise ValueError(t("msg_record_not_found"))
        
    doc_ref = conn.collection("records").document(doc_id)
    doc_ref.update({
        "Time": new_time_val,
        "IsScratch": bool(is_scratch)
    })

def delete_record_from_cloud(conn, timestamp_str, name, mode, record_id=None):
    """Delete a specific record from Firestore."""
    doc_id = _find_document_id(conn, timestamp_str, name, mode, record_id)
    if not doc_id:
        raise ValueError(t("msg_record_not_found"))
        
    conn.collection("records").document(doc_id).delete()
