import pytest
import pandas as pd
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.stats import calculate_ao5, iter_records_grouped_by_name_and_mode
from utils.stats import prepare_today_top5_data, get_personal_pb_rank
from utils.stats import prepare_daily_progress_data
from utils.data_manager import TIMEZONE
from datetime import datetime, timedelta

def test_calculate_ao5_less_than_5_records():
    """Test that Ao5 returns None if there are fewer than 5 records."""
    df = pd.DataFrame({"Time": [3.5, 3.6, 3.7, 3.8]})
    assert calculate_ao5(df) is None

def test_calculate_ao5_exact_5_records():
    """Test that Ao5 correctly drops the highest and lowest, returning the average of the middle 3."""
    # Times: 2.0, 3.0, 4.0, 5.0, 6.0
    # Min: 2.0 (dropped), Max: 6.0 (dropped)
    # Middle 3: 3.0, 4.0, 5.0
    # Average: (3.0 + 4.0 + 5.0) / 3 = 4.0
    df = pd.DataFrame({"Time": [5.0, 2.0, 4.0, 6.0, 3.0]})
    assert calculate_ao5(df) == 4.0

def test_calculate_ao5_more_than_5_records():
    """Test that Ao5 only considers the *last* 5 records in the DataFrame."""
    # DataFrame is assumed to be already sorted by Timestamp in the app.
    # We pass 6 records: we ignore the first one (0.0).
    # Last 5 times: 3.5, 9.9, 3.6, 3.8, 1.0
    # Min: 1.0 (dropped), Max: 9.9 (dropped)
    # Middle 3: 3.5, 3.6, 3.8
    # Average: (3.5 + 3.6 + 3.8) / 3 = 10.9 / 3 = 3.633...
    df = pd.DataFrame({"Time": [0.0, 3.5, 9.9, 3.6, 3.8, 1.0]})
    assert pytest.approx(calculate_ao5(df), 0.001) == 3.633

def test_iter_records_grouped_by_name_and_mode_groups_in_sorted_order():
    df = pd.DataFrame([
        {"Name": "B", "Mode": "Cycle", "Timestamp": "2026-03-31 10:00:00"},
        {"Name": "A", "Mode": "3-6-3", "Timestamp": "2026-03-31 10:01:00"},
        {"Name": "A", "Mode": "Cycle", "Timestamp": "2026-03-31 10:02:00"},
        {"Name": "B", "Mode": "3-6-3", "Timestamp": "2026-03-31 10:03:00"},
    ])

    grouped = iter_records_grouped_by_name_and_mode(df)

    assert [name for name, _ in grouped] == ["A", "B"]
    assert [mode for mode, _ in grouped[0][1]] == ["3-6-3", "Cycle"]
    assert [mode for mode, _ in grouped[1][1]] == ["3-6-3", "Cycle"]
    assert grouped[0][1][0][1]["Name"].tolist() == ["A"]
    assert grouped[1][1][1][1]["Name"].tolist() == ["B"]

def test_iter_records_grouped_by_name_and_mode_returns_empty_for_empty_input():
    df = pd.DataFrame(columns=["Name", "Mode", "Timestamp"])
    assert iter_records_grouped_by_name_and_mode(df) == []

def test_prepare_today_top5_data_filters_and_ranks():
    today = datetime.now(TIMEZONE)
    today_str = today.strftime("%Y-%m-%d")
    yesterday_str = (today - timedelta(days=1)).strftime("%Y-%m-%d")

    df = pd.DataFrame([
        {"Name": "Johnny", "Mode": "3-3-3", "Timestamp": f"{today_str} 10:00:00", "Time": 3.300, "IsScratch": False},
        {"Name": "Johnny", "Mode": "3-3-3", "Timestamp": f"{today_str} 10:01:00", "Time": 3.100, "IsScratch": False},
        {"Name": "Johnny", "Mode": "3-3-3", "Timestamp": f"{today_str} 10:02:00", "Time": 3.500, "IsScratch": False},
        {"Name": "Johnny", "Mode": "3-3-3", "Timestamp": f"{today_str} 10:03:00", "Time": 3.000, "IsScratch": False},
        {"Name": "Johnny", "Mode": "3-3-3", "Timestamp": f"{today_str} 10:04:00", "Time": 3.200, "IsScratch": False},
        {"Name": "Johnny", "Mode": "3-3-3", "Timestamp": f"{today_str} 10:05:00", "Time": 2.900, "IsScratch": False},
        {"Name": "Johnny", "Mode": "3-3-3", "Timestamp": f"{today_str} 10:06:00", "Time": 2.800, "IsScratch": True},
        {"Name": "Johnny", "Mode": "3-3-3", "Timestamp": f"{yesterday_str} 10:00:00", "Time": 2.700, "IsScratch": False},
    ])

    top5_df = prepare_today_top5_data(df)

    assert len(top5_df) == 5
    assert top5_df["Rank"].tolist() == [1, 2, 3, 4, 5]
    assert top5_df["Time"].tolist() == [2.9, 3.0, 3.1, 3.2, 3.3]

def test_get_personal_pb_rank_returns_rank_when_candidate_is_top5():
    valid_df = pd.DataFrame([
        {"Name": "Johnny", "Mode": "3-6-3", "Time": 5.50, "Timestamp": "2026-03-30 10:00:00"},
        {"Name": "Johnny", "Mode": "3-6-3", "Time": 5.60, "Timestamp": "2026-03-30 10:01:00"},
        {"Name": "Johnny", "Mode": "3-6-3", "Time": 5.70, "Timestamp": "2026-03-30 10:02:00"},
        {"Name": "Johnny", "Mode": "3-6-3", "Time": 5.80, "Timestamp": "2026-03-30 10:03:00"},
        {"Name": "Johnny", "Mode": "3-6-3", "Time": 5.90, "Timestamp": "2026-03-30 10:04:00"},
    ])

    assert get_personal_pb_rank(valid_df, "Johnny", "3-6-3", 5.45, "2026-03-31 09:00:00") == 1
    assert get_personal_pb_rank(valid_df, "Johnny", "3-6-3", 5.75, "2026-03-31 09:01:00") == 4
    assert get_personal_pb_rank(valid_df, "Johnny", "3-6-3", 6.10, "2026-03-31 09:02:00") is None

def test_get_personal_pb_rank_considers_pending_valid_attempts_in_rank_source():
    persisted_df = pd.DataFrame([
        {"Name": "Johnny", "Mode": "3-3-3", "Time": 5.00, "Timestamp": "2026-03-30 10:00:00"},
        {"Name": "Johnny", "Mode": "3-3-3", "Time": 5.10, "Timestamp": "2026-03-30 10:01:00"},
        {"Name": "Johnny", "Mode": "3-3-3", "Time": 5.20, "Timestamp": "2026-03-30 10:02:00"},
        {"Name": "Johnny", "Mode": "3-3-3", "Time": 5.30, "Timestamp": "2026-03-30 10:03:00"},
        {"Name": "Johnny", "Mode": "3-3-3", "Time": 5.40, "Timestamp": "2026-03-30 10:04:00"},
    ])
    pending_valid_df = pd.DataFrame([
        {"Name": "Johnny", "Mode": "3-3-3", "Time": 4.80, "Timestamp": "2026-03-31 09:30:00"},
        {"Name": "Johnny", "Mode": "3-3-3", "Time": 4.90, "Timestamp": "2026-03-31 09:31:00"},
    ])

    merged_rank_source_df = pd.concat([persisted_df, pending_valid_df], ignore_index=True)

    assert get_personal_pb_rank(
        persisted_df, "Johnny", "3-3-3", 5.35, "2026-03-31 10:00:00"
    ) == 5
    assert get_personal_pb_rank(
        merged_rank_source_df, "Johnny", "3-3-3", 5.35, "2026-03-31 10:00:00"
    ) is None


def test_prepare_daily_progress_data_does_not_mutate_input_df():
    today = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    df = pd.DataFrame([
        {"Timestamp": f"{today} 10:00:00", "Name": "Johnny", "Mode": "3-3-3", "Time": 3.2, "IsScratch": False},
    ])
    goals_df = pd.DataFrame([
        {"Name": "Johnny", "Mode": "3-3-3", "TargetTime": 3.5},
    ])

    _ = prepare_daily_progress_data(df, goals_df)

    assert "DateStr" not in df.columns
