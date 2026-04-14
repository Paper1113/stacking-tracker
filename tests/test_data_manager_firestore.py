import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.data_manager_firestore import FIRESTORE_BATCH_LIMIT, RECORD_ID_COL, sync_temp_logs_to_cloud


class FakeBatch:
    def __init__(self):
        self.operations = []
        self.commit_calls = 0

    def set(self, doc_ref, payload):
        self.operations.append((doc_ref.path, payload))

    def commit(self):
        self.commit_calls += 1


class FakeDocumentRef:
    def __init__(self, path):
        self.path = path


class FakeCollection:
    def __init__(self, name):
        self.name = name

    def document(self, doc_id):
        return FakeDocumentRef(f"{self.name}/{doc_id}")


class FakeConn:
    def __init__(self):
        self.batches = []

    def batch(self):
        batch = FakeBatch()
        self.batches.append(batch)
        return batch

    def collection(self, name):
        return FakeCollection(name)


def test_sync_temp_logs_to_cloud_chunks_large_batches():
    conn = FakeConn()
    temp_logs = [
        {
            "Timestamp": f"2026-03-31 10:{i % 60:02d}:00",
            "Name": "Johnny",
            "Mode": "3-3-3",
            "Time": 3.0 + i / 1000,
            "IsScratch": False,
            RECORD_ID_COL: f"record-{i}",
        }
        for i in range(FIRESTORE_BATCH_LIMIT + 2)
    ]

    sync_temp_logs_to_cloud(conn, temp_logs)

    assert len(conn.batches) == 2
    assert conn.batches[0].commit_calls == 1
    assert conn.batches[1].commit_calls == 1
    assert len(conn.batches[0].operations) == FIRESTORE_BATCH_LIMIT
    assert len(conn.batches[1].operations) == 2
