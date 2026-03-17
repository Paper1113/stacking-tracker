import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit.components.v1 as components
import os

_decimal_input_func = components.declare_component(
    "decimal_input",
    path=os.path.join(os.path.dirname(__file__), "decimal_input")
)

def decimal_input(key=None, value=None):
    return _decimal_input_func(key=key, default=value)

# --- Constants ---
TIMEZONE = ZoneInfo("Asia/Hong_Kong")
AVAILABLE_MODES = ["3-3-3", "3-6-3", "Cycle"]
DEFAULT_PLAYERS = ["Johnny", "Ashley"]
DATA_TTL = 300  # Cache data for 5 minutes (manually cleared after each save)

# --- i18n Translation Dictionary ---
TRANSLATIONS = {
    "zh-TW": {
        "subtitle": "快速記錄你的疊杯成績，挑戰 PB！",
        "daily_header": "📈 今日練習進度",
        "daily_expander": "👤 {name} 嘅今日進度",
        "daily_no_goals_match": "📌 今日未有符合 Goals 目標嘅練習紀錄。",
        "daily_no_goals_sheet": "📌 請於 Google Sheets 新增 `Goals` 分頁並設定 `TargetTime`。",
        "daily_no_records": "📌 今日暫無紀錄",
        "col_mode": "項目",
        "col_total": "總次數",
        "col_success": "達標數",
        "col_strict_rate": "嚴格達標率",
        "col_lenient_rate": "寬鬆達標率",
        "col_target": "目標",
        "ao5_header": "📊 平均 5 次 (Ao5)",
        "ao5_expander": "📊 最近 5 次平均 (Ao5)",
        "ao5_desc": "*去掉最快與最慢，取中間三次平均*",
        "ao5_mode": "📍 項目: {mode}",
        "ao5_need5": "📊 Ao5: 📌 選手需喺單一項目累積 5 次成績才會顯示",
        "ao5_no_records": "📊 Ao5: 暫無紀錄",
        "pb_header": "🏆 個人最佳 (PB)",
        "pb_expander": "🏆 個人最佳 (PB)",
        "pb_mode": "📍 項目: {mode}",
        "pb_no_records": "🏆 個人最佳 (PB): 暫無紀錄",
        "input_header": "新增練習紀錄",
        "input_player": "選手",
        "input_mode": "⏱️ 項目",
        "input_time": "⏳ 成績 (秒)",
        "btn_success": "✅ 成功 Success",
        "btn_dnf": "🔴 失誤 DNF",
        "temp_pool": "📥 待上傳記錄",
        "btn_sync": "💾 同步到雲端",
        "btn_clear": "🗑️ 清空",
        "msg_added": "已暫存 {time}s",
        "msg_synced": "✅ 所有數據已同步至雲端！",
        "sync_fail": "同步失敗：{err}",
        "fast_mode": "⚡ 快速記錄模式",
        "fast_mode_desc": "先暫存本地，之後再同步",
        "err_invalid_time": "時間無效！(不可為空或 0)",
        "msg_dnf": "❌ 已紀錄失誤 (DNF)：{name} - {mode} - {time}s",
        "msg_success": "✅ 已紀錄：{name} - {mode} - {time}s",
        "err_save_fail": "儲存失敗（請確保 Service Account 有編輯權限）：{err}",
        "err_read_fail": "讀取失敗（請檢查 Sheet 名稱是否為 Data）：{err}",
        "records_header": "📜 最近紀錄",
        "records_today": "📅 今日 ({date})",
        "records_past": "📆 過往紀錄 (按項目分組)",
        "col_date": "日期",
        "col_fastest": "最快",
        "col_players": "選手",
        "lang_label": "🌐 語言 / Language",
    },
    "en": {
        "subtitle": "Record your sport stacking times, beat your PB!",
        "daily_header": "📈 Today's Progress",
        "daily_expander": "👤 {name}'s Progress Today",
        "daily_no_goals_match": "📌 No practice records matching Goals targets today.",
        "daily_no_goals_sheet": "📌 Please add a `Goals` worksheet in Google Sheets with `TargetTime`.",
        "daily_no_records": "📌 No records today",
        "col_mode": "Mode",
        "col_total": "Total",
        "col_success": "Pass",
        "col_strict_rate": "Strict Rate",
        "col_lenient_rate": "Lenient Rate",
        "col_target": "Target",
        "ao5_header": "📊 Average of 5 (Ao5)",
        "ao5_expander": "📊 Average of 5 (Ao5)",
        "ao5_desc": "*Drop best & worst, average the middle 3*",
        "ao5_mode": "📍 Mode: {mode}",
        "ao5_need5": "📊 Ao5: 📌 Need at least 5 attempts in a single mode to display",
        "ao5_no_records": "📊 Ao5: No records",
        "pb_header": "🏆 Personal Best (PB)",
        "pb_expander": "🏆 Personal Best (PB)",
        "pb_mode": "📍 Mode: {mode}",
        "pb_no_records": "🏆 Personal Best (PB): No records",
        "input_header": "Add Practice Record",
        "input_player": "Player",
        "input_mode": "⏱️ Mode",
        "input_time": "⏳ Time (sec)",
        "btn_success": "✅ Success",
        "btn_dnf": "🔴 DNF",
        "temp_pool": "📥 Pending Records",
        "btn_sync": "💾 Sync to Cloud",
        "btn_clear": "🗑️ Clear",
        "msg_added": "Added {time}s to temp",
        "msg_synced": "✅ All data synced to cloud!",
        "sync_fail": "Sync failed: {err}",
        "fast_mode": "⚡ Fast Mode",
        "fast_mode_desc": "Save locally first, sync later",
        "err_invalid_time": "Invalid time! (cannot be empty or 0)",
        "msg_dnf": "❌ Recorded DNF: {name} - {mode} - {time}s",
        "msg_success": "✅ Recorded: {name} - {mode} - {time}s",
        "err_save_fail": "Save failed (ensure Service Account has edit access): {err}",
        "err_read_fail": "Read failed (check if worksheet is named Data): {err}",
        "records_header": "📜 Recent Records",
        "records_today": "📅 Today ({date})",
        "records_past": "📆 Past Records (grouped by mode)",
        "col_date": "Date",
        "col_fastest": "Fastest",
        "col_players": "Players",
        "lang_label": "🌐 語言 / Language",
    },
}

# Page configuration (responsive layout for mobile)
st.set_page_config(page_title="Stacking Tracker", layout="centered")

# --- Language Detection & Selection ---
# Detect browser language via JS and store in session state (runs once)
if 'lang_detected' not in st.session_state:
    st.session_state.lang_detected = False
if 'lang' not in st.session_state:
    st.session_state.lang = "zh-TW"  # Default to Traditional Chinese

# Inject JS to detect browser language (only on first load)
if not st.session_state.lang_detected:
    components.html("""
    <script>
    const lang = navigator.language || navigator.userLanguage || 'zh-TW';
    const isZh = lang.startsWith('zh');
    // Send result to Streamlit via query params workaround
    window.parent.postMessage({type: 'streamlit:setComponentValue', value: isZh ? 'zh-TW' : 'en'}, '*');
    </script>
    """, height=0)
    # Fallback: if language starts with 'zh' in accept-language, default to zh-TW
    st.session_state.lang_detected = True

# Language selector in sidebar
LANG_OPTIONS = {"繁體中文": "zh-TW", "English": "en"}
LANG_LABELS = list(LANG_OPTIONS.keys())
current_lang_idx = LANG_LABELS.index("繁體中文") if st.session_state.lang == "zh-TW" else LANG_LABELS.index("English")

selected_lang_label = st.sidebar.selectbox(
    "🌐 語言 / Language",
    LANG_LABELS,
    index=current_lang_idx,
    key="lang_selector"
)
st.session_state.lang = LANG_OPTIONS[selected_lang_label]

# Shortcut for translation lookup
def t(key, **kwargs):
    """Get translated string for the current language."""
    text = TRANSLATIONS.get(st.session_state.lang, TRANSLATIONS["zh-TW"]).get(key, key)
    return text.format(**kwargs) if kwargs else text

# --- Global CSS Styles ---
st.markdown("""
<style>
div.stButton > button {
    height: 80px;
    font-size: 24px !important;
    font-weight: bold;
    border-radius: 15px;
}
input[type="number"] {
    font-size: 20px !important;
    height: 50px !important;
}
/* Green background for the Success button */
div[data-testid="column"]:first-child div.stButton > button {
    background-color: #2e7d32;
    color: white;
    border: none;
}
div[data-testid="column"]:first-child div.stButton > button:hover {
    background-color: #1b5e20;
    color: white;
}
</style>
""", unsafe_allow_html=True)

st.title("⏱️ Stacking Tracker")
st.markdown(t("subtitle"))

# 1. Establish Google Sheets connection
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Read data from the "Data" worksheet
try:
    df = conn.read(worksheet="Data", ttl=DATA_TTL)

    # Strip leading single quotes from Mode (protection against Google Sheets date auto-format)
    if "Mode" in df.columns:
        df["Mode"] = df["Mode"].astype(str).str.lstrip("'")
        
    # Ensure IsScratch column is boolean
    if "IsScratch" in df.columns:
        df["IsScratch"] = df["IsScratch"].astype(str).str.upper() == "TRUE"
    else:
        df["IsScratch"] = False

    # Coerce Time column to numeric for calculations
    df["Time"] = pd.to_numeric(df["Time"], errors='coerce')
    
    # Build a filtered DataFrame excluding scratched (DNF) records
    valid_df = df[(df["Time"].notnull()) & (~df["IsScratch"])].copy()
except Exception as e:
    st.error(t("err_read_fail", err=e))
    df = pd.DataFrame(columns=["Timestamp", "Name", "Mode", "Time", "IsScratch"])
    valid_df = df.copy()

# 3. Read player names from the "Players" worksheet (fallback to Data or defaults)
try:
    players_df = conn.read(worksheet="Players", ttl=DATA_TTL)
    if "Name" in players_df.columns:
        names = players_df["Name"].dropna().astype(str).str.strip().tolist()
    else:
        col_name = str(players_df.columns[0]).strip()
        names = []
        if col_name and not col_name.startswith("Unnamed"):
            names.append(col_name)
        names.extend(players_df.iloc[:, 0].dropna().astype(str).str.strip().tolist())
except Exception:
    if not df.empty and "Name" in df.columns:
        names = df["Name"].dropna().astype(str).str.strip().unique().tolist()
    else:
        names = []

names = [n for n in names if n]
if not names:
    names = DEFAULT_PLAYERS

# 4. Read goal settings from the "Goals" worksheet
goals_df = pd.DataFrame(columns=["Name", "Mode", "TargetTime"])
try:
    g_df = conn.read(worksheet="Goals", ttl=DATA_TTL)
    if not g_df.empty and {"Mode", "TargetTime"}.issubset(g_df.columns):
        if "Name" not in g_df.columns:
            g_df["Name"] = "All"
        g_df["Name"] = g_df["Name"].fillna("All").astype(str).str.strip()
        g_df["Mode"] = g_df["Mode"].astype(str).str.strip().str.lstrip("'")
        g_df["TargetTime"] = pd.to_numeric(g_df["TargetTime"], errors='coerce')
        goals_df = g_df.dropna(subset=["TargetTime"])
except Exception:
    pass

# Guard: reset last_name if the player is no longer in the list
if 'last_name' in st.session_state and st.session_state.last_name not in names:
    st.session_state.last_name = names[0]


# ============================================================
# Main Input Section (with optional fast mode for 3-3-3)
# ============================================================
def input_section():
    # Initialize temp logs pool and fast mode state
    if 'temp_logs' not in st.session_state:
        st.session_state.temp_logs = []
    if 'fast_mode' not in st.session_state:
        st.session_state.fast_mode = False

    if 'last_name' not in st.session_state:
        st.session_state.last_name = names[0]
    if 'last_mode' not in st.session_state:
        st.session_state.last_mode = AVAILABLE_MODES[0]
    if 'input_time' not in st.session_state:
        st.session_state.input_time = None

    name_idx = names.index(st.session_state.last_name) if st.session_state.last_name in names else 0
    mode_idx = AVAILABLE_MODES.index(st.session_state.last_mode) if st.session_state.last_mode in AVAILABLE_MODES else 0

    st.subheader(t("input_header"))

    c1, c2 = st.columns(2)
    with c1:
        name = st.selectbox(t("input_player"), names, index=name_idx)
    with c2:
        mode = st.radio(t("input_mode"), AVAILABLE_MODES, index=mode_idx, horizontal=True)

    # Show fast mode toggle only for 3-3-3
    if mode == "3-3-3":
        fast_mode = st.toggle(t("fast_mode"), help=t("fast_mode_desc"), key="fast_mode_toggle")
        st.session_state.fast_mode = fast_mode
    else:
        st.session_state.fast_mode = False

    # Use st.text_input with dynamic key to allow clearing
    # Key changes when we want to reset the input
    if 'time_input_key' not in st.session_state:
        st.session_state.time_input_key = 0

    st.markdown(f"<div style='margin-bottom: 5px; font-size: 14px;'>{t('input_time')}</div>", unsafe_allow_html=True)
    time_str = st.text_input(
        t("input_time"),
        value="",
        key=f"time_text_input_{st.session_state.time_input_key}",
        label_visibility="collapsed",
        placeholder="0.000"
    )

    # Convert string to float
    try:
        time_val = float(time_str) if time_str else None
    except ValueError:
        time_val = None

    st.write("")

    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        submit_success = st.button(t("btn_success"), use_container_width=True)
    with btn_col2:
        submit_dnf = st.button(t("btn_dnf"), use_container_width=True, type="primary")

    if submit_success or submit_dnf:
        is_scratch = submit_dnf
        use_fast_mode = st.session_state.fast_mode

        if time_val is None or time_val <= 0:
            st.error(t("err_invalid_time"))
        else:
            timestamp_str = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
            safe_mode = f"'{mode}" if mode in ["3-3-3", "3-6-3"] else mode

            # Save to temp pool or upload to cloud
            if use_fast_mode:
                # Save to temp pool (instant, no network call)
                st.session_state.temp_logs.append({
                    "Timestamp": timestamp_str,
                    "Name": name,
                    "Mode": safe_mode,
                    "Time": time_val,
                    "IsScratch": is_scratch
                })
                st.toast(t("msg_added", time=f"{time_val:.3f}"), icon="⏱️")
            else:
                # Immediate upload to cloud (original behavior)
                try:
                    url = st.secrets.connections.gsheets.spreadsheet
                    ws = conn.client._client.open_by_url(url).worksheet("Data")
                    row_data = [timestamp_str, name, safe_mode, time_val, is_scratch]
                    ws.append_row(row_data, table_range="A1", value_input_option="USER_ENTERED")

                    if is_scratch:
                        st.warning(t("msg_dnf", name=name, mode=mode, time=time_val))
                    else:
                        st.success(t("msg_success", name=name, mode=mode, time=time_val))

                    st.cache_data.clear()
                except Exception as e:
                    st.error(t("err_save_fail", err=e))

            st.session_state.last_name = name
            st.session_state.last_mode = mode
            # Clear time input by incrementing the key (creates new input)
            st.session_state.time_input_key += 1
            st.rerun()

    # --- Temp Pool Display & Sync (only when fast mode is used) ---
    if st.session_state.temp_logs and st.session_state.fast_mode:
        st.divider()
        st.subheader(t("temp_pool"))

        temp_df = pd.DataFrame(st.session_state.temp_logs)
        temp_df['TimeDisplay'] = temp_df.apply(
            lambda row: f"❌ {row['Time']:.3f}s" if row.get('IsScratch', False) else f"{row['Time']:.3f}s", axis=1
        )
        st.dataframe(temp_df[['Name', 'Mode', 'TimeDisplay']], hide_index=True, use_container_width=True)

        sync_col, clear_col = st.columns(2)
        with sync_col:
            if st.button(t("btn_sync"), type="primary", use_container_width=True):
                try:
                    with st.spinner("同步中..."):
                        url = st.secrets.connections.gsheets.spreadsheet
                        ws = conn.client._client.open_by_url(url).worksheet("Data")

                        for log in st.session_state.temp_logs:
                            row_data = [log["Timestamp"], log["Name"], log["Mode"], log["Time"], log["IsScratch"]]
                            ws.append_row(row_data, table_range="A1", value_input_option="USER_ENTERED")

                        st.session_state.temp_logs = []
                        st.success(t("msg_synced"))
                        st.cache_data.clear()
                        st.rerun()
                except Exception as e:
                    st.error(t("sync_fail", err=e))

        with clear_col:
            if st.button(t("btn_clear"), use_container_width=True):
                st.session_state.temp_logs = []
                st.rerun()

input_section()

# ============================================================
# 📊 Stats Tabs (Daily/Ao5/PB)
# ============================================================
# Initialize empty DataFrames in case valid_df is empty
ao5_df = pd.DataFrame()
pb_df = pd.DataFrame()

if not valid_df.empty:
    valid_df_sorted = valid_df.sort_values(by='Timestamp')

    def calculate_ao5(group):
        """Calculate Ao5: drop best and worst from last 5, average middle 3."""
        if len(group) >= 5:
            last_5 = group.tail(5)['Time'].tolist()
            last_5.sort()
            return sum(last_5[1:4]) / 3
        return None

    # Prepare Ao5 data
    ao5_results = []
    for (a_name, a_mode), group in valid_df_sorted.groupby(['Name', 'Mode']):
        ao5 = calculate_ao5(group)
        if ao5 is not None:
            ao5_results.append({'Name': a_name, 'Mode': a_mode, 'Ao5': ao5})
    ao5_df = pd.DataFrame(ao5_results) if ao5_results else pd.DataFrame()

    # Prepare PB data
    idx = valid_df.groupby(['Name', 'Mode'])['Time'].idxmin()
    pb_df = valid_df.loc[idx, ['Name', 'Mode', 'Time', 'Timestamp']].copy()
    pb_df['Date'] = pd.to_datetime(pb_df['Timestamp'], errors='coerce').dt.strftime('%Y-%m-%d')
    pb_df['Time'] = pb_df['Time'].map('{:,.3f}s'.format)

# Prepare Daily Progress data
if not df.empty:
    today_str = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    df['DateStr'] = pd.to_datetime(df['Timestamp'], errors='coerce').dt.strftime('%Y-%m-%d')
    today_df = df[df['DateStr'] == today_str].copy()

    progress_data = []
    if not today_df.empty and not goals_df.empty:
        for (p_name, p_mode), group in today_df.groupby(['Name', 'Mode']):
            target = goals_df[((goals_df['Name'] == p_name) | (goals_df['Name'] == 'All')) & (goals_df['Mode'] == p_mode)]
            if not target.empty:
                target_time = target.sort_values(by='Name', ascending=False).iloc[0]['TargetTime']
                total_count = len(group)
                dnf_count = len(group[group['IsScratch']])
                valid_count = total_count - dnf_count
                valid_attempts = group[~group['IsScratch']]
                success_count = len(valid_attempts[pd.to_numeric(valid_attempts['Time'], errors='coerce') <= target_time])
                overall_rate = (success_count / total_count * 100) if total_count > 0 else 0.0
                valid_rate = (success_count / valid_count * 100) if valid_count > 0 else 0.0
                progress_data.append({
                    "Name": p_name,
                    t("col_mode"): p_mode,
                    t("col_total"): f"{total_count} (DNF: {dnf_count})",
                    t("col_success"): f"{success_count}/{total_count}",
                    t("col_strict_rate"): f"{overall_rate:.1f}%",
                    t("col_lenient_rate"): f"{valid_rate:.1f}%",
                    t("col_target"): f"≤{target_time}s"
                })
    progress_df = pd.DataFrame(progress_data) if progress_data else pd.DataFrame()
else:
    progress_df = pd.DataFrame()

# Create tabs for stats
tab_daily, tab_ao5, tab_pb = st.tabs([t("daily_header"), t("ao5_header"), t("pb_header")])

with tab_daily:
    if not progress_df.empty:
        for p_name in sorted(progress_df['Name'].unique()):
            with st.expander(t("daily_expander", name=p_name), expanded=True):
                p_df = progress_df[progress_df['Name'] == p_name].reset_index(drop=True)
                st.dataframe(p_df.drop(columns=['Name']), hide_index=True, use_container_width=True)
    else:
        if df.empty:
            st.info(t("daily_no_records"))
        elif goals_df.empty:
            st.info(t("daily_no_goals_sheet"))
        else:
            st.info(t("daily_no_goals_match"))

with tab_ao5:
    if not ao5_df.empty:
        ao5_df['Ao5'] = ao5_df['Ao5'].map('{:,.3f}s'.format)
        st.markdown(t("ao5_desc"))
        for m in sorted(ao5_df['Mode'].unique()):
            st.subheader(t("ao5_mode", mode=m))
            m_ao5_df = ao5_df[ao5_df['Mode'] == m].sort_values(by='Name').reset_index(drop=True)
            st.dataframe(m_ao5_df[['Name', 'Ao5']], hide_index=True, use_container_width=True)
    else:
        st.write(t("ao5_need5"))

with tab_pb:
    if not pb_df.empty:
        for m in sorted(pb_df['Mode'].unique()):
            st.subheader(t("pb_mode", mode=m))
            m_df = pb_df[pb_df['Mode'] == m].sort_values(by='Name').reset_index(drop=True)
            st.dataframe(m_df[['Name', 'Time', 'Date']], hide_index=True, use_container_width=True)
    else:
        st.write(t("pb_no_records"))

st.divider()

# ============================================================
# Records Display (last 500 records)
# ============================================================
st.subheader(t("records_header"))
if not df.empty:
    today_str = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    recent_df = df.sort_values(by="Timestamp", ascending=False).head(500).copy()
    recent_df['Date'] = pd.to_datetime(recent_df['Timestamp'], errors='coerce').dt.strftime('%Y-%m-%d')
    
    # --- Today's records: show each entry individually ---
    today_records = recent_df[recent_df['Date'] == today_str].copy()
    if not today_records.empty:
        st.markdown(f"### {t('records_today', date=today_str)}")
        today_records['Time'] = today_records.apply(
            lambda row: f"❌ {row['Time']:.3f}s (DNF)" if row.get('IsScratch', False) else f"{row['Time']:.3f}s", axis=1
        )
        st.dataframe(today_records[['Timestamp', 'Name', 'Mode', 'Time']], width="stretch", hide_index=True)
    
    # --- Past records: grouped by Mode > Date ---
    past_records = recent_df[recent_df['Date'] != today_str].copy()
    if not past_records.empty:
        st.markdown(f"### {t('records_past')}")
        # Group by Mode first, then show each date's summary
        for mode in sorted(past_records['Mode'].unique()):
            mode_records = past_records[past_records['Mode'] == mode]
            grouped_by_date = mode_records.groupby('Date').apply(
                lambda g: pd.Series({
                    t('col_total'): len(g),
                    'DNF': int(g['IsScratch'].sum()),
                    t('col_fastest'): f"{g.loc[~g['IsScratch'], 'Time'].min():.3f}s" if (~g['IsScratch']).any() else '-',
                    t('col_players'): ', '.join(g['Name'].unique()),
                }),
                include_groups=False
            ).sort_index(ascending=False).reset_index().rename(columns={'Date': t('col_date')})

            with st.expander(f"{mode}", expanded=False):
                st.dataframe(grouped_by_date[[t('col_date'), t('col_total'), 'DNF', t('col_fastest'), t('col_players')]], hide_index=True, use_container_width=True)