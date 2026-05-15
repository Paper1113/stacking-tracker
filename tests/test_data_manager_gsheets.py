import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

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
    def __init__(self, headers, fail_updates=False, fail_rows=None):
        self.headers = headers
        self.fail_updates = fail_updates
        self.fail_rows = set(fail_rows or [])
        self.updated_cells = []

    def row_values(self, row_idx):
        assert row_idx == 1
        return self.headers

    def update_cell(self, row_idx, col_idx, value):
        if self.fail_updates or row_idx in self.fail_rows:
            raise RuntimeError("write failed")
        self.updated_cells.append((row_idx, col_idx, value))


def test_get_data_worksheet_prefers_connection_client(monkeypatch):
    client = FakeWritableClient()
    conn = FakeConn(client)

    def fail_if_called():
        raise AssertionError("service-account secrets fallback should not be used")

    monkeypatch.setattr(gsheets_manager, "_get_data_worksheet_from_service_account_secrets", fail_if_called)

    worksheet = gsheets_manager._get_data_worksheet(conn)

    assert worksheet == "worksheet-from-conn-client"
    assert client.calls == [{"worksheet": "Data"}]


def test_get_data_worksheet_falls_back_when_client_missing(monkeypatch):
    """When conn.client is None, _get_data_worksheet should use the service-account fallback."""
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


def test_load_data_backfills_missing_record_ids(monkeypatch):
    import pandas as pd

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
    assert worksheet.updated_cells == [(2, 6, "generated-record-id")]


def test_load_data_keeps_legacy_record_ids_when_backfill_fails(monkeypatch):
    import pandas as pd

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

    df, valid_df = gsheets_manager.load_data(FakeConn(client=None))

    expected_ids = ["generated-1", "legacy-row-3", "legacy-row-4"]
    assert df["RecordId"].tolist() == expected_ids
    assert valid_df["RecordId"].tolist() == expected_ids
    assert worksheet.updated_cells == [(2, 6, "generated-1")]
    assert warnings == ["RecordId backfill skipped: write failed"]
