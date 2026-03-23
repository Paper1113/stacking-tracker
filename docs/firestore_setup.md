# Firestore Setup Guide

This guide sets up Firestore for this project before data migration from Google Sheets.

## 1. Create Firebase Project and Firestore

1. Open Firebase Console: https://console.firebase.google.com/
2. Create a new project (or reuse an existing one).
3. In the left menu, go to **Build -> Firestore Database**.
4. Click **Create database**.
5. Choose **Production mode** (recommended) and pick a region close to your users.

Save your `project_id` (for example: `stacking-tracker-prod`).

## 2. Create Service Account Key

1. Go to **Project settings -> Service accounts**.
2. Click **Generate new private key**.
3. Download the JSON key file.
4. Store it safely and do not commit it to git.

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

`firebase-admin` is already added to `requirements.txt`.

## 4. Configure Streamlit Secrets

Create local secrets:

```bash
mkdir -p .streamlit
cp secrets.example.toml .streamlit/secrets.toml
```

Then edit `.streamlit/secrets.toml`:

- Keep your current `[connections.gsheets]` config.
- Set `[firestore].project_id`.
- Replace `[firestore].service_account_json` with the full service account JSON content.

## 5. Apply Firestore Rules and Indexes

This repo includes:

- `firebase.json`
- `firestore.rules`
- `firestore.indexes.json`

Install Firebase CLI if needed:

```bash
npm install -g firebase-tools
firebase login
firebase use <your-project-id>
```

Deploy rules and indexes:

```bash
firebase deploy --only firestore:rules,firestore:indexes
```

## 6. Run Smoke Test

Use the provided script:

```bash
python scripts/firestore_smoke_test.py \
  --project-id <your-project-id> \
  --service-account </absolute/path/to/service-account.json>
```

If successful, it writes and reads:

- collection: `_healthchecks`
- document: `smoke-test`

Expected output includes: `Firestore smoke test passed.`

## 7. Streamlit-Side Firestore Client

Project helper:

- `utils/firestore_manager.py`

It reads secrets and initializes Firebase Admin SDK once via `st.cache_resource`.
You can import `get_firestore_client()` in migration or repository code.

## 8. Common Errors

1. `Missing [firestore] in Streamlit secrets`
   - Add `[firestore]` block in `.streamlit/secrets.toml`.

2. `service_account_json is not valid JSON`
   - Paste raw JSON content and keep escape sequences for newlines in private key (`\\n`).

3. Permission or index errors during query
   - Re-check project id.
   - Confirm `firebase deploy --only firestore:indexes` finished successfully.
