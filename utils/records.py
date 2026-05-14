import pandas as pd

RECORD_ID_COL = "RecordId"
LEGACY_ROW_PREFIX = "legacy-row-"
RECORD_COLUMNS = ["Timestamp", "Name", "Mode", "Time", "IsScratch", RECORD_ID_COL]


def normalize_records_dataframe(df: pd.DataFrame, missing_record_id_factory=None) -> pd.DataFrame:
    """Return records with the expected schema and normalized calculation columns."""
    if df is None or df.empty:
        return pd.DataFrame(columns=RECORD_COLUMNS)

    records_df = df.copy()
    for column in RECORD_COLUMNS:
        if column not in records_df.columns:
            records_df[column] = False if column == "IsScratch" else pd.NA

    records_df["Timestamp"] = records_df["Timestamp"].fillna("").astype(str)
    records_df["Name"] = records_df["Name"].fillna("").astype(str).str.strip()
    records_df["Mode"] = records_df["Mode"].fillna("").astype(str).str.strip().str.lstrip("'")
    records_df["IsScratch"] = records_df["IsScratch"].astype(str).str.upper() == "TRUE"
    records_df["Time"] = pd.to_numeric(records_df["Time"], errors="coerce")

    missing_mask = (
        records_df[RECORD_ID_COL].isna()
        | (records_df[RECORD_ID_COL].astype(str).str.strip() == "")
        | (records_df[RECORD_ID_COL].astype(str).str.lower() == "nan")
        | (records_df[RECORD_ID_COL].astype(str).str.lower() == "<na>")
    )
    records_df.loc[missing_mask, RECORD_ID_COL] = [
        (
            missing_record_id_factory(i)
            if missing_record_id_factory is not None
            else f"{LEGACY_ROW_PREFIX}{i + 2}"
        )
        for i in records_df.index[missing_mask]
    ]
    records_df[RECORD_ID_COL] = records_df[RECORD_ID_COL].astype(str)

    return records_df


def find_row_index(all_values, timestamp_str=None, name=None, mode=None, record_id=None):
    """Find the 1-based worksheet row index for a record."""
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

    for i, row in enumerate(all_values):
        if i == 0:
            continue
        if len(row) >= 3:
            r_ts, r_name, r_mode = row[0], row[1], row[2].lstrip("'")
            if r_ts == timestamp_str and r_name == name and r_mode == mode:
                return i + 1
    return None
