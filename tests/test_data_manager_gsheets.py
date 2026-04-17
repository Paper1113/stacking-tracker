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
