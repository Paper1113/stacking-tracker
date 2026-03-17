> **🌐 Language / 語言**: English | [繁體中文](README_ZH.md)

# ⏱️ Stacking Tracker

A lightweight practice logging app built for Sport Stacking enthusiasts and parents. Powered by Streamlit and Google Sheets, it lets you record every improvement anytime, anywhere — right from your phone.

## ✨ Features

### 📈 Daily Practice Progress
- Automatically tracks daily goal completion rates (strict & lenient calculations)
- Goals are configured per player/mode via a Google Sheets `Goals` worksheet
- Each player's progress is displayed independently

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
- Grouped by mode with the date the PB was set
- Includes a Top 5 PB ranking per mode (fastest attempts overall)

### 🛡️ Reliability & Cache Management
- **Manual Refresh**: A "Refresh Data" button gives users control to instantly sync with the latest Google Sheets data, bypassing Streamlit cache
- **API Resilience**: Powered by `tenacity`, all Google Sheets data fetches and uploads have automated retry logic (up to 3 attempts) to prevent crashes from temporary network timeouts

### 🔄 CI/CD & Automated Testing
- Protected by **GitHub Actions** workflows
- Core logic (like Ao5 rules) is guarded by **pytest** unit tests that run automatically on every push or PR

### ❌ Scratch / DNF Support
- Mark dropped-cup or incomplete attempts as Scratch / DNF
- DNF records are excluded from PB and Ao5 calculations but the time is preserved for reference
- Goal completion rates offer both strict (includes DNF) and lenient (excludes DNF) calculations

### 🧒 Child-Friendly UI
- Extra-large buttons (green for Success, red for DNF) — designed so even a 4-year-old can self-record
- Optimized number input for mobile numeric keypad
- Input fields auto-clear after each save
- Uses a custom Streamlit component for mobile-friendly decimal input (iOS Safari numeric keypad with decimal)

### 📜 Records Overview
- Today's records shown individually with full detail
- Past records grouped by date + mode with summary stats (total attempts, DNFs, fastest time)

### 🌐 Bilingual Support
- Auto-detects browser language and defaults to Traditional Chinese or English
- Manual language toggle in sidebar — switch anytime without losing data
- All UI text (headers, buttons, messages, column labels) updates instantly

## 🛠️ Tech Stack
- **Frontend/Backend**: [Streamlit](https://streamlit.io/) 1.55+
- **Database**: [Google Sheets](https://www.google.com/sheets/about/) (via `st-gsheets-connection`)
- **Resilience**: `tenacity` (API retries)
- **Testing**: `pytest`, GitHub Actions
- **Language**: Python 3.9+

## 🚀 Quick Start

### 1. Prepare Google Sheets

Create a Google Sheet with the following **3 worksheets**:

#### `Data` Worksheet (Required)
Header row:

| Timestamp | Name | Mode | Time | IsScratch |
|-----------|------|------|------|-----------|

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
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install streamlit st-gsheets-connection pandas pytest tenacity

# Configure secrets
mkdir .streamlit
# Place your secrets.toml in the .streamlit/ directory

# Run the app
streamlit run streamlit_app.py
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
│   └── test_stats.py   # Pytest coverage for Ao5 calculations
├── utils/              # Utility modules
│   ├── data_manager.py # Google Sheets connection & CRUD logic
│   ├── i18n.py         # Translations & language selection
│   └── stats.py        # Ao5, PB, and Progress calculations
├── .streamlit/
│   └── secrets.toml    # Google Sheets credentials (not committed)
├── README.md           # English documentation
└── README_ZH.md        # Chinese documentation
```
