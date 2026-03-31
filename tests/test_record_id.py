import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.data_manager_gsheets import _find_row_index


class DummyWorksheet:
    def __init__(self, values):
        self._values = values

    def get_all_values(self):
        return self._values


def test_find_row_index_prefers_record_id_when_duplicates_exist():
    ws = DummyWorksheet([
        ["Timestamp", "Name", "Mode", "Time", "IsScratch", "RecordId"],
        ["2026-03-20 10:10:10", "Johnny", "'3-3-3", "3.111", "FALSE", "rec-1"],
        ["2026-03-20 10:10:10", "Johnny", "'3-3-3", "3.222", "FALSE", "rec-2"],
    ])

    row_idx = _find_row_index(
        ws,
        timestamp_str="2026-03-20 10:10:10",
        name="Johnny",
        mode="3-3-3",
        record_id="rec-2"
    )
    assert row_idx == 3


def test_find_row_index_supports_legacy_row_record_id():
    ws = DummyWorksheet([
        ["Timestamp", "Name", "Mode", "Time", "IsScratch"],
        ["2026-03-20 10:10:10", "Johnny", "'3-3-3", "3.111", "FALSE"],
        ["2026-03-20 10:10:11", "Johnny", "'3-3-3", "3.222", "FALSE"],
    ])

    row_idx = _find_row_index(ws, record_id="legacy-row-3")
    assert row_idx == 3


def test_find_row_index_falls_back_to_composite_match():
    ws = DummyWorksheet([
        ["Timestamp", "Name", "Mode", "Time", "IsScratch"],
        ["2026-03-20 10:10:10", "Johnny", "'3-3-3", "3.111", "FALSE"],
    ])

    row_idx = _find_row_index(
        ws,
        timestamp_str="2026-03-20 10:10:10",
        name="Johnny",
        mode="3-3-3"
    )
    assert row_idx == 2


def test_find_row_index_legacy_id_mismatch_falls_back_to_composite():
    ws = DummyWorksheet([
        ["Timestamp", "Name", "Mode", "Time", "IsScratch"],
        ["2026-03-20 10:10:00", "Ashley", "'3-3-3", "3.111", "FALSE"],
        ["2026-03-20 10:10:10", "Johnny", "'3-3-3", "3.222", "FALSE"],
    ])

    row_idx = _find_row_index(
        ws,
        timestamp_str="2026-03-20 10:10:10",
        name="Johnny",
        mode="3-3-3",
        record_id="legacy-row-2",
    )
    assert row_idx == 3
