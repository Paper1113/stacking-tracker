import streamlit as st
import streamlit.components.v1 as components

# --- Constants ---
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
        "syncing": "同步中...",
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
        "syncing": "Syncing...",
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

def t(key, **kwargs):
    """Get translated string for the current language."""
    text = TRANSLATIONS.get(st.session_state.lang, TRANSLATIONS["zh-TW"]).get(key, key)
    return text.format(**kwargs) if kwargs else text

def setup_language_selector():
    """Injects JS language detection and sets up sidebar selection."""
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
