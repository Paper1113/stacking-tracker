import json
from typing import Any, Mapping

import firebase_admin
import streamlit as st
from firebase_admin import credentials, firestore


class FirestoreConfigError(RuntimeError):
    """Raised when Firestore configuration is missing or invalid."""


def _to_plain_dict(value: Any) -> dict:
    """Convert Streamlit secrets objects into a plain dict."""
    if isinstance(value, Mapping):
        return {k: _to_plain_dict(v) for k, v in value.items()}
    return value


def _load_firestore_secrets() -> tuple[str, dict]:
    """
    Load Firestore config from Streamlit secrets.

    Expected format in secrets.toml:
      [firestore]
      project_id = "your-project-id"
      service_account_json = "{...full service account json...}"
    """
    if "firestore" not in st.secrets:
        raise FirestoreConfigError(
            "Missing [firestore] in Streamlit secrets. See docs/firestore_setup.md"
        )

    fs_cfg = _to_plain_dict(st.secrets["firestore"])
    project_id = str(fs_cfg.get("project_id", "")).strip()
    service_account_json = fs_cfg.get("service_account_json")

    if not project_id:
        raise FirestoreConfigError("Missing firestore.project_id in secrets.")
    if not service_account_json:
        raise FirestoreConfigError("Missing firestore.service_account_json in secrets.")

    if isinstance(service_account_json, str):
        try:
            service_account_info = json.loads(service_account_json)
        except json.JSONDecodeError as exc:
            raise FirestoreConfigError(
                "firestore.service_account_json is not valid JSON."
            ) from exc
    elif isinstance(service_account_json, Mapping):
        service_account_info = _to_plain_dict(service_account_json)
    else:
        raise FirestoreConfigError(
            "firestore.service_account_json must be a JSON string or object."
        )

    return project_id, service_account_info


@st.cache_resource(show_spinner=False)
def get_firestore_client() -> firestore.Client:
    """Initialize Firebase Admin app once and return a Firestore client."""
    project_id, service_account_info = _load_firestore_secrets()

    try:
        app = firebase_admin.get_app()
    except ValueError:
        cred = credentials.Certificate(service_account_info)
        app = firebase_admin.initialize_app(cred, {"projectId": project_id})

    return firestore.client(app=app)
