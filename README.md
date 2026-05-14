> **🌐 Language / 語言**: English | [繁體中文](README_ZH.md)

# ⏱️ Stacking Tracker

A lightweight practice logging app built for Sport Stacking enthusiasts and parents. Powered by Streamlit with Google Sheets as the backend, it lets you record every improvement anytime, anywhere — right from your phone.

## ✨ Features

### 📈 Daily Practice Progress
- Automatically tracks daily goal completion rates (strict & lenient calculations)
- Goals are configured per player/mode via a Google Sheets `Goals` worksheet
- Each player's progress is displayed independently

### ⚡ Today's Top 5 Fastest
- Added between **Daily Practice Progress** and **Ao5** tabs
- Grouped by **player → mode**, showing today's top 5 valid attempts (Scratch excluded)
- Each table shows rank, time, gap from the fastest attempt, and timestamp for quick comparison

### ⚡ Fast Mode (Batch Sync)
- Opt-in toggle specifically for 3-3-3 mode to support rapid, back-to-back attempts
- Temporarily saves records locally to a pending pool without network delays
- Batch uploads all pending records to Google Sheets with a single click (uses `append_rows` for extreme efficiency)

### 📊 Average of 5 (Ao5)
- Calculates the average of the last 5 valid attempts
- Drops the best and worst times, averages the middle 3 (WSSA standard)
- Grouped by stacking mode

### 🏆 Personal Best (PB)
- Tracks each player's fastest time per mode
- Features an **interactive trend chart (Line Chart)** to visualize progress over time
- Grouped by **player → mode**, with both levels collapsed by default for cleaner browsing
- Shows a trend chart and Top 5 PB table for each player+mode section
- PB Top 5 tables include a **Gap** column so you can compare each result against the #1 time at a glance
- When a new valid record enters that player's top 5 PB for a mode, a toast notification shows the new PB rank

### 🛡️ Reliability & Cache Management
- **In-Memory State Sync (0-Read Optimization)**: Drastically reduces UI lag and API quotas by persisting the dataset in `st.session_state`. Record additions, updates, and deletions mutate the UI directly instantly without triggering full database reads.
- **Manual Refresh**: A "Refresh Data" button gives users control to instantly sync with the latest cloud data, overriding the local session state.
- **API Resilience**: Powered by `tenacity`, Google Sheets data fetches use automated retry logic (up to 3 attempts) to prevent crashes from temporary network timeouts.
- **Stable Record Targeting**: Each record now carries a unique `RecordId`, so update/delete actions always target the intended row even when timestamp/name/mode are duplicated.

### 🔄 CI/CD & Automated Testing
- Protected by **GitHub Actions** workflows
- Core logic (like Ao5 rules) is guarded by **pytest** unit tests that run automatically on every push or PR

### ❌ Scratch Support
- Mark dropped-cup or incomplete attempts as Scratch
- Scratch records are excluded from PB and Ao5 calculations but the time is preserved for reference
- Goal completion rates offer both strict (includes Scratch) and lenient (excludes Scratch) calculations

### 🧒 Child-Friendly UI
- Extra-large buttons (green for Success, red for Scratch) — designed so even a 4-year-old can self-record
- Optimized number input for mobile numeric keypad
- Input fields auto-clear after each save
- Uses a custom Streamlit component for mobile-friendly decimal input (iOS Safari numeric keypad with decimal)
- Includes an optional **backup native number input**, hidden by default and controlled from the sidebar
- Displays the current player + mode selection clearly to reduce mis-taps

### 📜 Records Overview
- Today's records are grouped by **player → mode** and show detailed attempts (timestamp, player, time, Scratch marker)
- Past records are grouped by **player → mode**, with both levels collapsed by default for cleaner browsing
- Each past mode section shows a **daily summary**: Date, Total attempts (`Total (Scratch: x)`), Scratch rate, and Fastest completion
- **Edit & Delete**: Modify or remove today's records from the main records section
- Delete actions include an explicit confirmation step to prevent accidental removal

### 🌐 Bilingual Support
- Auto-detects browser language and defaults to Traditional Chinese or English
- Manual language toggle in sidebar — switch anytime without losing data
- All UI text (headers, buttons, messages, column labels) updates instantly

## 🛠️ Tech Stack
- **Frontend/Backend**: [Streamlit](https://streamlit.io/) 1.55+
- **Database**: [Google Sheets](https://www.google.com/sheets/about/) via `st-gsheets-connection`
- **Resilience**: `tenacity` (API retries)
- **Testing**: `pytest`, GitHub Actions
- **Language**: Python 3.13 (runtime/devcontainer target)

## 🚀 Quick Start

### 1. Prepare Google Sheets

Create a Google Sheet with the following **3 worksheets**:

#### `Data` Worksheet (Required)
Header row:

| Timestamp | Name | Mode | Time | IsScratch | RecordId |
|-----------|------|------|------|-----------|----------|

- `RecordId` is a unique identifier for each row; legacy rows without it are handled automatically by the app

#### `Players` Worksheet (Recommended)
Header row:

| Name |
|------|
| Johnny |
| Ashley |

#### `Goals` Worksheet (Recommended)
Header row:

| Name | Mode | TargetTime |
|------|------|------------|
| All | 3-3-3 | 3.999 |
| All | 3-6-3 | 5.999 |
| Johnny | 3-3-3 | 3.500 |

- Set `Name` to `All` for a universal target; use a specific name for player-specific goals
- `TargetTime` is the maximum time allowed to count as a success (≤ this value = pass)

### 2. Configure Streamlit Secrets

When deploying on Streamlit Cloud, add the following in **Advanced Settings** → **Secrets**:

```toml
[connections.gsheets]
spreadsheet = "YOUR_GOOGLE_SHEET_URL"
```

### 3. Local Development

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS / Linux
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Configure secrets
mkdir .streamlit
# Place your secrets.toml in the .streamlit/ directory

# Run the app
python3 -m streamlit run streamlit_app.py
```

## 📁 Project Structure

```text
stacking-tracker/
├── .github/
│   └── workflows/
│       └── test.yml    # CI/CD pipeline for automated testing
├── streamlit_app.py    # Main application (UI Layout)
├── config.json         # Application constants (e.g., Modes, Data TTL)
├── i18n.json           # Externalized bilingual translation strings
├── requirements.txt    # Python dependencies
├── .gitignore          # Git ignore rules
├── tests/              # Unit tests
│   ├── test_stats.py   # Pytest coverage for Ao5 calculations
│   └── test_record_id.py # RecordId row-matching safety tests
├── utils/              # Utility modules
│   ├── data_manager.py           # Google Sheets data manager compatibility entrypoint
│   ├── data_manager_gsheets.py   # Google Sheets connection & CRUD logic
│   ├── i18n.py                   # Translations & language selection
│   └── stats.py                  # Ao5, PB, and Progress calculations
├── .streamlit/
│   └── secrets.toml    # Google Sheets credentials (not committed)
├── README.md           # English documentation
└── README_ZH.md        # Chinese documentation
```
