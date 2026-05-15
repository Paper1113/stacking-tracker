import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest

import utils.data_manager_gsheets as gsheets_manager


class FakeWritableClient:
    def __init__(self):
        self.calls = []

    def _select_worksheet(self, **kwargs):
        self.calls.append(kwargs)
        return "worksheet-from-conn-client"


class FakeConn:
    def __init__(self, client):
        self.client = client


class FakeWorksheet:
    def __init__(self, headers, fail_updates=False, fail_rows=None, all_values=None):
        self.headers = headers
        self.fail_updates = fail_updates
        self.fail_rows = set(fail_rows or [])
        self.all_values = all_values or []
        self.row_values_calls = 0
        self.batch_updates = []
        self.range_updates = []
        self.updated_cells = []

    def row_values(self, row_idx):
        assert row_idx == 1
        self.row_values_calls += 1
        return self.headers

    def update_cell(self, row_idx, col_idx, value):
        if self.fail_updates or row_idx in self.fail_rows:
            raise RuntimeError("write failed")
        self.updated_cells.append((row_idx, col_idx, value))

    def batch_update(self, data, **kwargs):
        rows = {
            int("".join(ch for ch in update["range"] if ch.isdigit()))
            for update in data
        }
        if self.fail_updates or rows.intersection(self.fail_rows):
            raise RuntimeError("write failed")
        self.batch_updates.append((data, kwargs))

    def get_all_values(self):
        return self.all_values

    def update(self, range_name, values=None, **kwargs):
        if self.fail_updates:
            raise RuntimeError("write failed")
        self.range_updates.append((range_name, values, kwargs))


def test_get_data_worksheet_prefers_connection_client(monkeypatch):
    gsheets_manager._DATA_WORKSHEET_CACHE.clear()
    client = FakeWritableClient()
    conn = FakeConn(client)

    def fail_if_called():
        raise AssertionError("service-account secrets fallback should not be used")

    monkeypatch.setattr(gsheets_manager, "_get_data_worksheet_from_service_account_secrets", fail_if_called)

    worksheet = gsheets_manager._get_data_worksheet(conn)
    cached_worksheet = gsheets_manager._get_data_worksheet(conn)

    assert worksheet == "worksheet-from-conn-client"
    assert cached_worksheet == "worksheet-from-conn-client"
    assert client.calls == [{"worksheet": "Data"}]


def test_get_data_worksheet_falls_back_when_client_missing(monkeypatch):
    """When conn.client is None, _get_data_worksheet should use the service-account fallback."""
    gsheets_manager._DATA_WORKSHEET_CACHE.clear()
    conn = FakeConn(client=None)

    monkeypatch.setattr(
        gsheets_manager,
        "_get_data_worksheet_from_service_account_secrets",
        lambda: "worksheet-from-service-account",
    )

    worksheet = gsheets_manager._get_data_worksheet(conn)
    assert worksheet == "worksheet-from-service-account"


def test_get_data_worksheet_falls_back_when_no_select_worksheet(monkeypatch):
    """When conn.client exists but lacks _select_worksheet, fallback should be used."""
    gsheets_manager._DATA_WORKSHEET_CACHE.clear()

    class ClientWithoutSelect:
        pass

    conn = FakeConn(client=ClientWithoutSelect())

    monkeypatch.setattr(
        gsheets_manager,
        "_get_data_worksheet_from_service_account_secrets",
        lambda: "worksheet-from-service-account",
    )

    worksheet = gsheets_manager._get_data_worksheet(conn)
    assert worksheet == "worksheet-from-service-account"


def test_write_with_retry_retries_transient_failure(monkeypatch):
    monkeypatch.setattr(gsheets_manager._write_with_retry.retry, "sleep", lambda _: None)
    calls = {"count": 0}

    def flaky_operation():
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("temporary outage")
        return "ok"

    assert gsheets_manager._write_with_retry(flaky_operation) == "ok"
    assert calls["count"] == 2


def test_write_with_retry_reraises_final_error(monkeypatch):
    monkeypatch.setattr(gsheets_manager._write_with_retry.retry, "sleep", lambda _: None)
    calls = {"count": 0}

    def failing_operation():
        calls["count"] += 1
        raise RuntimeError("persistent outage")

    with pytest.raises(RuntimeError, match="persistent outage"):
        gsheets_manager._write_with_retry(failing_operation)

    assert calls["count"] == 3


def test_load_data_backfills_missing_record_ids_once(monkeypatch):
    import pandas as pd

    gsheets_manager._RECORD_ID_COL_CACHE.clear()
    worksheet = FakeWorksheet(["Timestamp", "Name", "Mode", "Time", "IsScratch", "RecordId"])
    raw_df = pd.DataFrame([
        {
            "Timestamp": "2026-03-20 10:10:10",
            "Name": "Johnny",
            "Mode": "'3-3-3",
            "Time": "3.111",
            "IsScratch": "FALSE",
            "RecordId": "",
        }
    ])

    monkeypatch.setattr(gsheets_manager, "_read_with_retry", lambda conn, worksheet_name: raw_df)
    monkeypatch.setattr(gsheets_manager, "_get_data_worksheet", lambda conn: worksheet)
    monkeypatch.setattr(gsheets_manager.uuid, "uuid4", lambda: "generated-record-id")

    df, valid_df = gsheets_manager.load_data(FakeConn(client=None))

    assert df["RecordId"].tolist() == ["generated-record-id"]
    assert valid_df["RecordId"].tolist() == ["generated-record-id"]
    assert worksheet.row_values_calls == 1
    assert worksheet.updated_cells == []
    assert worksheet.batch_updates == [(
        [{"range": "F2", "values": [["generated-record-id"]]}],
        {"value_input_option": "RAW"},
    )]


def test_load_data_skips_backfill_when_record_ids_already_exist(monkeypatch):
    import pandas as pd

    gsheets_manager._RECORD_ID_COL_CACHE.clear()
    worksheet = FakeWorksheet(["Timestamp", "Name", "Mode", "Time", "IsScratch", "RecordId"])
    raw_df = pd.DataFrame([
        {
            "Timestamp": "2026-03-20 10:10:10",
            "Name": "Johnny",
            "Mode": "'3-3-3",
            "Time": "3.111",
            "IsScratch": "FALSE",
            "RecordId": "record-1",
        },
    ])

    monkeypatch.setattr(gsheets_manager, "_read_with_retry", lambda conn, worksheet_name: raw_df)
    monkeypatch.setattr(gsheets_manager, "_get_data_worksheet", lambda conn: worksheet)

    df, valid_df = gsheets_manager.load_data(FakeConn(client=None))

    assert df["RecordId"].tolist() == ["record-1"]
    assert valid_df["RecordId"].tolist() == ["record-1"]
    assert worksheet.row_values_calls == 0
    assert worksheet.updated_cells == []
    assert worksheet.batch_updates == []


def test_load_data_keeps_legacy_record_ids_when_backfill_fails(monkeypatch):
    import pandas as pd

    gsheets_manager._RECORD_ID_COL_CACHE.clear()
    worksheet = FakeWorksheet(
        ["Timestamp", "Name", "Mode", "Time", "IsScratch", "RecordId"],
        fail_updates=True,
    )
    raw_df = pd.DataFrame([
        {
            "Timestamp": "2026-03-20 10:10:10",
            "Name": "Johnny",
            "Mode": "'3-3-3",
            "Time": "3.111",
            "IsScratch": "FALSE",
            "RecordId": "",
        },
        {
            "Timestamp": "2026-03-20 10:10:10",
            "Name": "Johnny",
            "Mode": "'3-3-3",
            "Time": "3.222",
            "IsScratch": "FALSE",
            "RecordId": "",
        },
    ])
    warnings = []

    monkeypatch.setattr(gsheets_manager, "_read_with_retry", lambda conn, worksheet_name: raw_df)
    monkeypatch.setattr(gsheets_manager, "_get_data_worksheet", lambda conn: worksheet)
    monkeypatch.setattr(gsheets_manager.uuid, "uuid4", lambda: "generated-record-id")
    monkeypatch.setattr(gsheets_manager.st, "warning", lambda message: warnings.append(message))
    monkeypatch.setattr(gsheets_manager._write_with_retry.retry, "sleep", lambda _: None)

    df, valid_df = gsheets_manager.load_data(FakeConn(client=None))

    assert df["RecordId"].tolist() == ["legacy-row-2", "legacy-row-3"]
    assert valid_df["RecordId"].tolist() == ["legacy-row-2", "legacy-row-3"]
    assert warnings == ["RecordId backfill skipped: write failed"]


def test_load_data_retains_successful_record_ids_when_backfill_partially_fails(monkeypatch):
    import pandas as pd

    gsheets_manager._RECORD_ID_COL_CACHE.clear()
    worksheet = FakeWorksheet(
        ["Timestamp", "Name", "Mode", "Time", "IsScratch", "RecordId"],
        fail_rows={3},
    )
    raw_df = pd.DataFrame([
        {
            "Timestamp": "2026-03-20 10:10:10",
            "Name": "Johnny",
            "Mode": "'3-3-3",
            "Time": "3.111",
            "IsScratch": "FALSE",
            "RecordId": "",
        },
        {
            "Timestamp": "2026-03-20 10:10:10",
            "Name": "Johnny",
            "Mode": "'3-3-3",
            "Time": "3.222",
            "IsScratch": "FALSE",
            "RecordId": "",
        },
        {
            "Timestamp": "2026-03-20 10:10:10",
            "Name": "Johnny",
            "Mode": "'3-3-3",
            "Time": "3.333",
            "IsScratch": "FALSE",
            "RecordId": "",
        },
    ])
    generated_ids = iter(["generated-1", "generated-2", "generated-3"])
    warnings = []

    monkeypatch.setattr(gsheets_manager, "_read_with_retry", lambda conn, worksheet_name: raw_df)
    monkeypatch.setattr(gsheets_manager, "_get_data_worksheet", lambda conn: worksheet)
    monkeypatch.setattr(gsheets_manager.uuid, "uuid4", lambda: next(generated_ids))
    monkeypatch.setattr(gsheets_manager.st, "warning", lambda message: warnings.append(message))
    monkeypatch.setattr(gsheets_manager._write_with_retry.retry, "sleep", lambda _: None)
    monkeypatch.setattr(gsheets_manager, "BACKFILL_BATCH_SIZE", 1)

    df, valid_df = gsheets_manager.load_data(FakeConn(client=None))

    expected_ids = ["generated-1", "legacy-row-3", "legacy-row-4"]
    assert df["RecordId"].tolist() == expected_ids
    assert valid_df["RecordId"].tolist() == expected_ids
    assert worksheet.batch_updates == [(
        [{"range": "F2", "values": [["generated-1"]]}],
        {"value_input_option": "RAW"},
    )]
    assert warnings == ["RecordId backfill skipped: write failed"]


def test_backfill_revalidates_record_id_column_after_header_reorder(monkeypatch):
    gsheets_manager._RECORD_ID_COL_CACHE.clear()
    worksheet = FakeWorksheet(["Timestamp", "Name", "Mode", "Time", "IsScratch", "RecordId"])

    assert gsheets_manager._ensure_record_id_header(worksheet) == 6

    worksheet.headers = ["Timestamp", "Name", "Mode", "Time", "IsScratch", "Notes", "RecordId"]
    monkeypatch.setattr(gsheets_manager, "_get_data_worksheet", lambda conn: worksheet)

    successful_backfills = gsheets_manager._backfill_missing_record_ids(
        FakeConn(client=None),
        [(2, "generated-record-id")],
    )

    assert successful_backfills == [(2, "generated-record-id")]
    assert worksheet.row_values_calls == 2
    assert worksheet.batch_updates == [(
        [{"range": "G2", "values": [["generated-record-id"]]}],
        {"value_input_option": "RAW"},
    )]


def test_ensure_record_id_header_caches_column_lookup():
    gsheets_manager._RECORD_ID_COL_CACHE.clear()
    worksheet = FakeWorksheet(["Timestamp", "Name", "Mode", "Time", "IsScratch", "RecordId"])

    assert gsheets_manager._ensure_record_id_header(worksheet) == 6
    assert gsheets_manager._ensure_record_id_header(worksheet) == 6

    assert worksheet.row_values_calls == 1


def test_update_record_updates_time_and_scratch_in_single_range(monkeypatch):
    worksheet = FakeWorksheet(
        ["Timestamp", "Name", "Mode", "Time", "IsScratch", "RecordId"],
        all_values=[
            ["Timestamp", "Name", "Mode", "Time", "IsScratch", "RecordId"],
            ["2026-03-20 10:10:10", "Johnny", "'3-3-3", "3.111", "FALSE", "record-1"],
        ],
    )

    monkeypatch.setattr(gsheets_manager, "_get_data_worksheet", lambda conn: worksheet)

    gsheets_manager.update_record_in_cloud(
        FakeConn(client=None),
        "2026-03-20 10:10:10",
        "Johnny",
        "3-3-3",
        3.222,
        True,
        record_id="record-1",
    )

    assert worksheet.range_updates == [(
        "D2:E2",
        [[3.222, True]],
        {"value_input_option": "USER_ENTERED"},
    )]
    assert worksheet.updated_cells == []
