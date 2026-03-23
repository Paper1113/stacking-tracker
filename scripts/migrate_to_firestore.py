import os
import sys

# Ensure the parent directory is in the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from utils.data_manager import load_data, load_players, load_goals, get_connection
from utils.firestore_manager import get_firestore_client

def main():
    print("Connecting to Google Sheets...")
    conn = get_connection()
    df, valid_df = load_data(conn)
    players = load_players(conn, [])
    goals_df = load_goals(conn)

    print("Connecting to Firestore...")
    db = get_firestore_client()

    print(f"Migrating {len(df)} records from Data sheet...")
    batch = db.batch()
    records_count = 0
    
    for _, row in df.iterrows():
        # Get the unique RecordId, if it fails to exist we skip or create one
        record_id = row.get("RecordId")
        if not record_id or pd.isna(record_id):
            import uuid
            record_id = str(uuid.uuid4())
            
        doc_ref = db.collection("records").document(str(record_id))
        
        # Build document data
        # Handle nan or missing values properly
        doc_data = {
            "Timestamp": str(row["Timestamp"]) if pd.notnull(row["Timestamp"]) else "",
            "Name": str(row["Name"]) if pd.notnull(row["Name"]) else "",
            "Mode": str(row["Mode"]).lstrip("'") if pd.notnull(row["Mode"]) else "",
            "Time": float(row["Time"]) if pd.notnull(row["Time"]) else None,
            "IsScratch": bool(row["IsScratch"]) if pd.notnull(row["IsScratch"]) else False,
            "RecordId": str(record_id)
        }
        batch.set(doc_ref, doc_data)
        records_count += 1
        
        # Commit batch every 400 documents (Firestore limit is 500)
        if records_count % 400 == 0:
            batch.commit()
            print(f"Committed {records_count} records...")
            batch = db.batch()
            
    # Commit remaining
    if records_count % 400 != 0:
        batch.commit()
        print(f"Committed remaining records. Total logic: {records_count}")

    print(f"Migrating {len(players)} players...")
    for player in players:
        # Use player name as document ID to ensure uniqueness, or just store list
        if player.strip():
            db.collection("players").document(player.strip()).set({"Name": player.strip(), "isActive": True})

    print(f"Migrating {len(goals_df)} goals...")
    for _, row in goals_df.iterrows():
        p_name = str(row["Name"]).strip()
        m_mode = str(row["Mode"]).lstrip("'").strip()
        t_time = float(row["TargetTime"]) if pd.notnull(row["TargetTime"]) else 0.0
        
        doc_id = f"{p_name}_{m_mode}".replace("/", "-")
        db.collection("goals").document(doc_id).set({
            "Name": p_name,
            "Mode": m_mode,
            "TargetTime": t_time
        })

    print("✅ Migration completed successfully!")

if __name__ == "__main__":
    main()
