#!/usr/bin/env python3
"""
Simple Firestore smoke test.

Usage:
  python scripts/firestore_smoke_test.py \
    --project-id your-project-id \
    --service-account /absolute/path/to/service-account.json
"""

import argparse
import datetime as dt
import json
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Firestore smoke test")
    parser.add_argument("--project-id", required=True, help="Firebase project id")
    parser.add_argument(
        "--service-account",
        required=True,
        help="Path to Firebase service account JSON file",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    service_account_path = Path(args.service_account).expanduser().resolve()
    if not service_account_path.exists():
        raise FileNotFoundError(f"Service account file not found: {service_account_path}")

    with service_account_path.open("r", encoding="utf-8") as f:
        service_account_info = json.load(f)

    cred = credentials.Certificate(service_account_info)
    app = firebase_admin.initialize_app(cred, {"projectId": args.project_id})
    db = firestore.client(app=app)

    now_utc = dt.datetime.now(dt.timezone.utc)
    doc_ref = db.collection("_healthchecks").document("smoke-test")
    payload = {
        "status": "ok",
        "updatedAt": now_utc,
        "updatedBy": "scripts/firestore_smoke_test.py",
    }
    doc_ref.set(payload, merge=True)
    snapshot = doc_ref.get()

    if not snapshot.exists:
        raise RuntimeError("Smoke test failed: document was not written.")

    print("Firestore smoke test passed.")
    print(f"Project: {args.project_id}")
    print(f"Document: _healthchecks/smoke-test")
    print(f"Data: {snapshot.to_dict()}")


if __name__ == "__main__":
    main()

