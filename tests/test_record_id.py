import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.records import find_row_index, normalize_records_dataframe


def test_find_row_index_prefers_record_id_when_duplicates_exist():
    values = [
        ["Timestamp", "Name", "Mode", "Time", "IsScratch", "RecordId"],
        ["2026-03-20 10:10:10", "Johnny", "'3-3-3", "3.111", "FALSE", "rec-1"],
        ["2026-03-20 10:10:10", "Johnny", "'3-3-3", "3.222", "FALSE", "rec-2"],
    ]

    row_idx = find_row_index(
        values,
        timestamp_str="2026-03-20 10:10:10",
        name="Johnny",
        mode="3-3-3",
        record_id="rec-2"
    )
    assert row_idx == 3


def test_find_row_index_supports_legacy_row_record_id():
    values = [
        ["Timestamp", "Name", "Mode", "Time", "IsScratch"],
        ["2026-03-20 10:10:10", "Johnny", "'3-3-3", "3.111", "FALSE"],
        ["2026-03-20 10:10:11", "Johnny", "'3-3-3", "3.222", "FALSE"],
    ]

    row_idx = find_row_index(values, record_id="legacy-row-3")
    assert row_idx == 3


def test_find_row_index_falls_back_to_composite_match():
    values = [
        ["Timestamp", "Name", "Mode", "Time", "IsScratch"],
        ["2026-03-20 10:10:10", "Johnny", "'3-3-3", "3.111", "FALSE"],
    ]

    row_idx = find_row_index(
        values,
        timestamp_str="2026-03-20 10:10:10",
        name="Johnny",
        mode="3-3-3"
    )
    assert row_idx == 2


def test_find_row_index_legacy_id_mismatch_falls_back_to_composite():
    values = [
        ["Timestamp", "Name", "Mode", "Time", "IsScratch"],
        ["2026-03-20 10:10:00", "Ashley", "'3-3-3", "3.111", "FALSE"],
        ["2026-03-20 10:10:10", "Johnny", "'3-3-3", "3.222", "FALSE"],
    ]

    row_idx = find_row_index(
        values,
        timestamp_str="2026-03-20 10:10:10",
        name="Johnny",
        mode="3-3-3",
        record_id="legacy-row-2",
    )
    assert row_idx == 3


def test_normalize_records_dataframe_adds_missing_columns_without_dropping_rows():
    import pandas as pd

    df = pd.DataFrame([
        {"Timestamp": "2026-03-20 10:10:10", "Name": " Johnny ", "Mode": "'3-3-3"},
    ])

    normalized_df = normalize_records_dataframe(df)

    assert normalized_df["Name"].tolist() == ["Johnny"]
    assert normalized_df["Mode"].tolist() == ["3-3-3"]
    assert normalized_df["Time"].isna().tolist() == [True]
    assert normalized_df["IsScratch"].tolist() == [False]
    assert normalized_df["RecordId"].tolist() == ["legacy-row-2"]


def test_normalize_records_dataframe_accepts_custom_record_id_factory():
    import pandas as pd

    df = pd.DataFrame([
        {"Timestamp": "2026-03-20 10:10:10", "Name": "Johnny", "Mode": "3-3-3"},
    ])

    normalized_df = normalize_records_dataframe(
        df,
        missing_record_id_factory=lambda idx: f"uuid-for-row-{idx}",
    )

    assert normalized_df["RecordId"].tolist() == ["uuid-for-row-0"]
