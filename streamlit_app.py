import streamlit as st
import pandas as pd
from datetime import datetime
import os
import uuid
import streamlit.components.v1 as components

from utils.i18n import t, setup_language_selector, AVAILABLE_MODES
from utils.data_manager import (
    get_connection, load_data, load_players, load_goals,
    get_current_timestamp, save_record_to_cloud, sync_temp_logs_to_cloud,
    update_record_in_cloud, delete_record_from_cloud,
    TIMEZONE
)
from utils.stats import (
    DAILY_PROGRESS_COLUMNS,
    prepare_ao5_data,
    prepare_daily_best_data,
    prepare_daily_progress_data,
    prepare_top_pb_attempts,
    iter_records_grouped_by_name_and_mode,
    prepare_today_top5_data,
    get_personal_pb_rank,
)

_decimal_input_func = components.declare_component(
    "decimal_input",
    path=os.path.join(os.path.dirname(__file__), "decimal_input")
)

def decimal_input(key=None, value=None):
    component_value = _decimal_input_func(key=key, default=value, value=value)

    fallback_value = 0.0
    if st.session_state.get("show_backup_time_input", False):
        with st.expander(t("input_time_fallback_label")):
            st.caption(t("input_time_fallback_help"))
            fallback_value = st.number_input(
                t("input_time"),
                min_value=0.0,
                step=0.001,
                format="%.3f",
                value=float(value or 0.0),
                key=f"{key}_native" if key else "time_decimal_input_native",
                label_visibility="collapsed",
            )

    if component_value is not None:
        return component_value
    return fallback_value if fallback_value > 0 else None

def queue_toast(message: str, icon: str = "ℹ️"):
    if 'pending_toasts' not in st.session_state:
        st.session_state.pending_toasts = []
    st.session_state.pending_toasts.append({"message": message, "icon": icon})

def flush_queued_toasts():
    pending_toasts = st.session_state.pop("pending_toasts", [])
    for toast in pending_toasts:
        st.toast(toast.get("message", ""), icon=toast.get("icon", "ℹ️"))

def format_record(row):
    ts = str(row.get('Timestamp', ''))
    time_part = ts[11:19] if len(ts) >= 19 else ts
    if pd.notnull(row.get('Time')):
        time_text = f"{float(row['Time']):.3f}s"
    else:
        time_text = "-"
    display_time = f"❌ {time_text} (DNF)" if row.get('IsScratch', False) else time_text
    return f"{time_part} | {row['Name']} | {row['Mode']} | {display_time}"

# Page configuration (responsive layout for mobile)
st.set_page_config(page_title="Stacking Tracker", layout="centered")

# JS language detection setup
setup_language_selector()

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
/* Explicit styles for submit buttons (avoid affecting other column buttons) */
div.st-key-submit_success_btn div.stButton > button {
    background-color: #2e7d32 !important;
    color: white !important;
    border: none !important;
}
div.st-key-submit_success_btn div.stButton > button:hover {
    background-color: #1b5e20 !important;
    color: white !important;
}
div.st-key-submit_dnf_btn div.stButton > button {
    background-color: #c62828 !important;
    color: white !important;
    border: none !important;
}
div.st-key-submit_dnf_btn div.stButton > button:hover {
    background-color: #8e0000 !important;
    color: white !important;
}

/* Mode selector card styling */
div[class*="st-key-mode_card_"] div.stButton > button {
    height: 72px;
    font-size: clamp(12px, 3.8vw, 22px) !important;
    border-radius: 14px;
    border: 2px solid #d0d7de;
    padding-left: 0.35rem !important;
    padding-right: 0.35rem !important;
}
div[class*="st-key-mode_card_"] div.stButton > button[kind="secondary"] {
    background-color: #ffffff;
    color: #1f2937;
}
div[class*="st-key-mode_card_"] div.stButton > button[kind="primary"] {
    background-color: #111827;
    color: #ffffff;
    border-color: #111827;
}

/* Keep mode cards in a single row on mobile */
div.st-key-mode_cards_row div[data-testid="stHorizontalBlock"] {
    display: flex;
    flex-wrap: nowrap;
    gap: 0.35rem;
    width: 100%;
    overflow: hidden;
}
div.st-key-mode_cards_row div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
div.st-key-mode_cards_row div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
    min-width: 0 !important;
    flex: 1 1 0 !important;
    width: 0 !important;
}

/* Keep submit buttons in one horizontal row on mobile */
div.st-key-submit_buttons_row div[data-testid="stHorizontalBlock"] {
    display: flex;
    flex-wrap: nowrap;
    gap: 0.5rem;
    width: 100%;
    overflow: hidden;
}
div.st-key-submit_buttons_row div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
div.st-key-submit_buttons_row div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
    min-width: 0 !important;
    flex: 1 1 0 !important;
    width: 0 !important;
}
</style>
""", unsafe_allow_html=True)

st.title("⏱️ Stacking Tracker")
st.markdown(t("subtitle"))
flush_queued_toasts()

# --- Data Loading ---
conn = get_connection()

if 'app_data_df' not in st.session_state or 'app_valid_df' not in st.session_state:
    _df, _valid_df = load_data(conn)
    st.session_state.app_data_df = _df.copy()
    st.session_state.app_valid_df = _valid_df.copy()

df = st.session_state.app_data_df
valid_df = st.session_state.app_valid_df

# For names fallback if Players sheet fails but Data sheet has names
default_names_from_data = df["Name"].dropna().astype(str).str.strip().unique().tolist() if (not df.empty and "Name" in df.columns) else []
names = load_players(conn, default_names_from_data)
goals_df = load_goals(conn)

# Guard: reset last_name if the player is no longer in the list
if 'last_name' in st.session_state and st.session_state.last_name not in names:
    st.session_state.last_name = names[0]

# Add Manual Refresh Button
st.sidebar.markdown("---")
if st.sidebar.button(t("btn_refresh"), use_container_width=True):
    st.cache_data.clear()
    if 'app_data_df' in st.session_state:
        del st.session_state.app_data_df
    if 'app_valid_df' in st.session_state:
        del st.session_state.app_valid_df
    st.rerun()
st.sidebar.toggle(
    t("toggle_backup_time_input"),
    key="show_backup_time_input",
    value=st.session_state.get("show_backup_time_input", False),
    help=t("toggle_backup_time_input_help"),
)


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
    if 'selected_player' not in st.session_state:
        st.session_state.selected_player = st.session_state.last_name
    if 'selected_mode' not in st.session_state:
        st.session_state.selected_mode = st.session_state.last_mode
    if 'input_time' not in st.session_state:
        st.session_state.input_time = None

    if st.session_state.selected_player not in names:
        st.session_state.selected_player = names[0]
    if st.session_state.selected_mode not in AVAILABLE_MODES:
        st.session_state.selected_mode = AVAILABLE_MODES[0]

    name_idx = names.index(st.session_state.selected_player) if st.session_state.selected_player in names else 0
    st.subheader(t("input_header"))

    st.selectbox(t("input_player"), names, index=name_idx, key="selected_player")
    st.markdown(
        f"<div style='margin-bottom: 8px; font-size: 14px;'>{t('input_mode')}</div>",
        unsafe_allow_html=True
    )
    with st.container(key="mode_cards_row"):
        mode_cols = st.columns(len(AVAILABLE_MODES))
        for idx, available_mode in enumerate(AVAILABLE_MODES):
            with mode_cols[idx]:
                clicked = st.button(
                    available_mode,
                    key=f"mode_card_{idx}",
                    use_container_width=True,
                    type="primary" if st.session_state.selected_mode == available_mode else "secondary"
                )
                if clicked and st.session_state.selected_mode != available_mode:
                    st.session_state.selected_mode = available_mode
                    st.rerun()

    name = st.session_state.selected_player
    mode = st.session_state.selected_mode
    st.caption(t("input_current_selection", name=name, mode=mode))

    # Show fast mode toggle only for 3-3-3
    if mode == "3-3-3":
        fast_mode = st.toggle(t("fast_mode"), help=t("fast_mode_desc"), key="fast_mode_toggle")
        st.session_state.fast_mode = fast_mode
    else:
        st.session_state.fast_mode = False

    # Use custom decimal_input with dynamic key to allow clearing
    # Key changes when we want to reset the input
    if 'time_input_key' not in st.session_state:
        st.session_state.time_input_key = 0

    st.markdown(f"<div style='margin-bottom: 5px; font-size: 14px;'>{t('input_time')}</div>", unsafe_allow_html=True)
    time_val = decimal_input(
        key=f"time_decimal_input_{st.session_state.time_input_key}"
    )

    st.write("")

    with st.container(key="submit_buttons_row"):
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            submit_success = st.button(t("btn_success"), use_container_width=True, key="submit_success_btn")
        with btn_col2:
            submit_dnf = st.button(t("btn_dnf"), use_container_width=True, key="submit_dnf_btn")

    if submit_success or submit_dnf:
        is_scratch = submit_dnf
        use_fast_mode = st.session_state.fast_mode

        if time_val is None or time_val <= 0:
            st.error(t("err_invalid_time"))
        else:
            timestamp_str = get_current_timestamp()
            pb_rank = None
            if not is_scratch:
                # Keep PB notifications consistent across fast-mode and immediate uploads:
                # always rank against persisted valid rows + unsynced valid temp logs.
                pending_valid_logs = [log for log in st.session_state.temp_logs if not log.get('IsScratch', False)]
                pending_valid_df = pd.DataFrame(pending_valid_logs)
                rank_source_df = st.session_state.app_valid_df.copy()
                if not pending_valid_df.empty:
                    rank_source_df = pd.concat([rank_source_df, pending_valid_df], ignore_index=True)
                pb_rank = get_personal_pb_rank(rank_source_df, name, mode, time_val, timestamp_str)

            # Save to temp pool or upload to cloud
            if use_fast_mode:
                # Save to temp pool (instant, no network call)
                st.session_state.temp_logs.append({
                    "Timestamp": timestamp_str,
                    "Name": name,
                    "Mode": mode,
                    "Time": time_val,
                    "IsScratch": is_scratch
                })
                queue_toast(t("msg_added", time=f"{time_val:.3f}"), icon="⏱️")
                if pb_rank is not None:
                    queue_toast(
                        t("msg_pb_rank", name=name, mode=mode, time=f"{time_val:.3f}", rank=pb_rank),
                        icon="🏆"
                    )
                
                st.session_state.last_name = name
                st.session_state.last_mode = mode
                st.session_state.time_input_key += 1
                st.rerun()
            else:
                # Immediate upload to cloud (original behavior)
                try:
                    record_id = save_record_to_cloud(conn, timestamp_str, name, mode, time_val, is_scratch)

                    new_row = {"Timestamp": timestamp_str, "Name": name, "Mode": mode, "Time": time_val, "IsScratch": is_scratch, "RecordId": record_id}
                    st.session_state.app_data_df = pd.concat([st.session_state.app_data_df, pd.DataFrame([new_row])], ignore_index=True)
                    if not is_scratch:
                        st.session_state.app_valid_df = pd.concat([st.session_state.app_valid_df, pd.DataFrame([new_row])], ignore_index=True)

                    if is_scratch:
                        st.warning(t("msg_dnf", name=name, mode=mode, time=time_val))
                    else:
                        st.success(t("msg_success", name=name, mode=mode, time=time_val))
                        if pb_rank is not None:
                            queue_toast(
                                t("msg_pb_rank", name=name, mode=mode, time=f"{time_val:.3f}", rank=pb_rank),
                                icon="🏆"
                            )
                    
                    st.session_state.last_name = name
                    st.session_state.last_mode = mode
                    # Clear time input by incrementing the key (creates new input)
                    st.session_state.time_input_key += 1
                    st.rerun()
                except Exception as e:
                    st.error(t("err_save_fail", err=e))

    # --- Temp Pool Display & Sync ---
    if st.session_state.temp_logs:
        st.divider()
        st.subheader(t("temp_pool"))
        if not st.session_state.fast_mode:
            st.caption(t("temp_pool_unsynced_note"))

        temp_df = pd.DataFrame(st.session_state.temp_logs)
        temp_df['TimeDisplay'] = temp_df.apply(
            lambda row: f"❌ {row['Time']:.3f}s" if row.get('IsScratch', False) else f"{row['Time']:.3f}s", axis=1
        )
        st.dataframe(temp_df[['Name', 'Mode', 'TimeDisplay']], hide_index=True, width="stretch")

        sync_col, clear_col = st.columns(2)
        with sync_col:
            if st.button(t("btn_sync"), type="primary", use_container_width=True):
                try:
                    with st.spinner(t("syncing")):
                        new_rows = []
                        for log in st.session_state.temp_logs:
                            synced_log = dict(log)
                            synced_log['RecordId'] = synced_log.get('RecordId') or str(uuid.uuid4())
                            new_rows.append(synced_log)
                            
                        sync_temp_logs_to_cloud(conn, new_rows)
                        
                        st.session_state.app_data_df = pd.concat([st.session_state.app_data_df, pd.DataFrame(new_rows)], ignore_index=True)
                        valid_logs = [log for log in new_rows if not log.get('IsScratch', False)]
                        if valid_logs:
                            st.session_state.app_valid_df = pd.concat([st.session_state.app_valid_df, pd.DataFrame(valid_logs)], ignore_index=True)

                        st.session_state.temp_logs = []
                        st.success(t("msg_synced"))
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
valid_df_sorted = valid_df.sort_values(by='Timestamp') if not valid_df.empty else pd.DataFrame()

ao5_df = prepare_ao5_data(valid_df_sorted)
pb_df = prepare_daily_best_data(valid_df)
progress_df = prepare_daily_progress_data(df, goals_df)
today_top5_df = prepare_today_top5_data(df)

# Create tabs for stats
tab_daily, tab_today_top5, tab_ao5, tab_pb = st.tabs([
    t("daily_header"),
    t("today_top5_header"),
    t("ao5_header"),
    t("pb_header")
])

with tab_daily:
    if not progress_df.empty:
        progress_display_columns = {
            DAILY_PROGRESS_COLUMNS["mode"]: t("col_mode"),
            DAILY_PROGRESS_COLUMNS["total"]: t("col_total"),
            DAILY_PROGRESS_COLUMNS["success"]: t("col_success"),
            DAILY_PROGRESS_COLUMNS["strict_rate"]: t("col_strict_rate"),
            DAILY_PROGRESS_COLUMNS["lenient_rate"]: t("col_lenient_rate"),
            DAILY_PROGRESS_COLUMNS["target"]: t("col_target"),
        }
        progress_display_order = [
            progress_display_columns[DAILY_PROGRESS_COLUMNS["mode"]],
            progress_display_columns[DAILY_PROGRESS_COLUMNS["total"]],
            progress_display_columns[DAILY_PROGRESS_COLUMNS["success"]],
            progress_display_columns[DAILY_PROGRESS_COLUMNS["strict_rate"]],
            progress_display_columns[DAILY_PROGRESS_COLUMNS["lenient_rate"]],
            progress_display_columns[DAILY_PROGRESS_COLUMNS["target"]],
        ]
        for p_name in sorted(progress_df['Name'].unique()):
            with st.expander(t("daily_expander", name=p_name), expanded=True):
                p_df = progress_df[progress_df['Name'] == p_name].reset_index(drop=True)
                display_df = p_df.drop(columns=['Name']).rename(columns=progress_display_columns)
                st.dataframe(display_df[progress_display_order], hide_index=True, width="stretch")
    else:
        if df.empty:
            st.info(t("daily_no_records"))
        elif goals_df.empty:
            st.info(t("daily_no_goals_sheet"))
        else:
            st.info(t("daily_no_goals_match"))

with tab_today_top5:
    if not today_top5_df.empty:
        st.caption(t("today_top5_desc"))
        for p_name in sorted(today_top5_df['Name'].dropna().unique()):
            with st.expander(t("records_player_group", name=p_name), expanded=False):
                p_top5_df = today_top5_df[today_top5_df['Name'] == p_name].copy()
                for m in sorted(p_top5_df['Mode'].dropna().unique()):
                    with st.expander(t("records_mode_group", mode=m), expanded=False):
                        pm_top5_df = p_top5_df[p_top5_df['Mode'] == m].copy().sort_values(by='Rank')
                        pm_top5_df['Time'] = pm_top5_df['Time'].map('{:,.3f}s'.format)
                        pm_top5_df['Gap'] = pm_top5_df['Gap'].map(
                            lambda x: "" if pd.isna(x) or x == 0 else f"+{x:.3f}s"
                        )
                        pm_top5_df['Timestamp'] = pd.to_datetime(
                            pm_top5_df['Timestamp'], errors='coerce'
                        ).dt.strftime('%H:%M:%S').fillna('-')
                        display_df = pm_top5_df.rename(columns={
                            'Rank': t("col_rank"),
                            'Time': t("col_time"),
                            'Gap': t("col_gap"),
                            'Timestamp': t("col_timestamp")
                        })
                        st.dataframe(
                            display_df[[t("col_rank"), t("col_time"), t("col_gap"), t("col_timestamp")]],
                            hide_index=True,
                            width="stretch"
                        )
    else:
        st.info(t("today_top5_no_records"))

with tab_ao5:
    if not ao5_df.empty:
        ao5_df['Ao5'] = ao5_df['Ao5'].map('{:,.3f}s'.format)
        st.markdown(t("ao5_desc"))
        for m in sorted(ao5_df['Mode'].unique()):
            st.subheader(t("ao5_mode", mode=m))
            m_ao5_df = ao5_df[ao5_df['Mode'] == m].sort_values(by='Name').reset_index(drop=True)
            st.dataframe(m_ao5_df[['Name', 'Ao5']], hide_index=True, width="stretch")
    else:
        st.write(t("ao5_need5"))

with tab_pb:
    if not pb_df.empty:
        for p_name in sorted(pb_df['Name'].dropna().unique()):
            with st.expander(t("pb_player_group", name=p_name), expanded=False):
                p_pb_df = pb_df[pb_df['Name'] == p_name].copy()
                for m in sorted(p_pb_df['Mode'].dropna().unique()):
                    with st.expander(t("pb_mode", mode=m), expanded=False):
                        pm_df = p_pb_df[p_pb_df['Mode'] == m].copy()
                        chart_data = pm_df.sort_values(by='Date')[['Date', 'Time']].set_index('Date')

                        # Show trend chart for this player+mode.
                        st.line_chart(chart_data)

                        # Show Top 5 PB attempts for this player+mode.
                        p_df = prepare_top_pb_attempts(valid_df, p_name, m)
                        if not p_df.empty:
                            display_df = p_df.copy()
                            display_df['Time'] = display_df['Time'].map('{:,.3f}s'.format)
                            display_df['Gap'] = display_df['Gap'].map(
                                lambda x: "" if pd.isna(x) or x == 0 else f"+{x:.3f}s"
                            )
                            display_df = display_df.rename(columns={
                                'Rank': t("col_rank"),
                                'Time': t("col_time"),
                                'Gap': t("col_gap"),
                                'Date': t("col_date"),
                            })
                            st.dataframe(
                                display_df[[t("col_rank"), t("col_time"), t("col_gap"), t("col_date")]],
                                hide_index=True,
                                width="stretch",
                            )
                        else:
                            st.write(t("pb_no_records"))
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
    recent_df['TimeDisplay'] = recent_df.apply(
        lambda row: f"❌ {float(row['Time']):.3f}s (DNF)" if row.get('IsScratch', False) and pd.notnull(row['Time'])
        else (f"{float(row['Time']):.3f}s" if pd.notnull(row['Time']) else "-"),
        axis=1
    )

    today_records = recent_df[recent_df['Date'] == today_str].copy()
    past_records = recent_df[recent_df['Date'] != today_str].copy()

    if not today_records.empty:
        st.markdown(f"### {t('records_today', date=today_str)}")
        for name, mode_groups in iter_records_grouped_by_name_and_mode(today_records):
            with st.expander(t("records_player_group", name=name), expanded=False):
                for mode, mode_records in mode_groups:
                    with st.expander(t("records_mode_group", mode=mode), expanded=False):
                        st.dataframe(
                            mode_records[['Timestamp', 'Name', 'TimeDisplay']],
                            hide_index=True,
                            width="stretch"
                        )

        st.write("")
        with st.expander(t("records_edit_header"), expanded=False):
            edit_options = today_records.copy()
            if edit_options.empty:
                st.info(t("records_edit_empty"))
            else:
                pending_delete_key = "main_pending_delete_uid"
                edit_options['UID'] = edit_options['RecordId'].astype(str)
                uid_to_display = dict(zip(edit_options['UID'], edit_options.apply(format_record, axis=1)))

                selected_uid = st.selectbox(
                    t("edit_select_record"),
                    options=edit_options['UID'].tolist(),
                    format_func=lambda uid: uid_to_display[uid],
                    key="main_edit_record_select"
                )

                selected_row = edit_options[edit_options['UID'] == selected_uid].iloc[0]
                uid_safe = selected_uid.replace("|", "_")
                orig_ts = selected_row['Timestamp']
                orig_name = selected_row['Name']
                orig_mode = selected_row['Mode']
                orig_record_id = str(selected_row.get('RecordId', ''))
                orig_time = float(selected_row['Time']) if pd.notnull(selected_row['Time']) else 0.0
                orig_scratch = bool(selected_row.get('IsScratch', False))

                new_time_val = st.number_input(
                    t("edit_time"),
                    min_value=0.0,
                    value=float(orig_time),
                    step=0.001,
                    format="%.3f",
                    key=f"main_edit_time_input_{uid_safe}"
                )
                new_scratch = st.checkbox(
                    t("edit_dnf"),
                    value=orig_scratch,
                    key=f"main_edit_dnf_{uid_safe}"
                )

                col_u, col_d = st.columns(2)
                with col_u:
                    if st.button(t("btn_update"), use_container_width=True, type="primary", key="main_btn_update"):
                        if new_time_val is None or new_time_val <= 0:
                            st.error(t("err_invalid_time"))
                        else:
                            try:
                                update_record_in_cloud(
                                    conn,
                                    orig_ts,
                                    orig_name,
                                    orig_mode,
                                    new_time_val,
                                    new_scratch,
                                    record_id=orig_record_id
                                )
                                
                                mask = st.session_state.app_data_df['RecordId'] == orig_record_id
                                st.session_state.app_data_df.loc[mask, 'Time'] = new_time_val
                                st.session_state.app_data_df.loc[mask, 'IsScratch'] = new_scratch
                                
                                st.session_state.app_valid_df = st.session_state.app_data_df[
                                    (st.session_state.app_data_df['Time'].notnull()) & (~st.session_state.app_data_df['IsScratch'])
                                ]
                                
                                st.success(t("msg_update_success"))
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")

                with col_d:
                    if st.button(t("btn_delete"), use_container_width=True, key="main_btn_delete"):
                        st.session_state[pending_delete_key] = selected_uid

                if st.session_state.get(pending_delete_key) == selected_uid:
                    st.warning(t("delete_confirm_prompt"))
                    confirm_col, cancel_col = st.columns(2)
                    with confirm_col:
                        if st.button(
                            t("btn_confirm_delete"),
                            use_container_width=True,
                            type="primary",
                            key=f"main_btn_confirm_delete_{uid_safe}"
                        ):
                            try:
                                delete_record_from_cloud(
                                    conn,
                                    orig_ts,
                                    orig_name,
                                    orig_mode,
                                    record_id=orig_record_id
                                )
                                
                                st.session_state.app_data_df = st.session_state.app_data_df[st.session_state.app_data_df['RecordId'] != orig_record_id]
                                st.session_state.app_valid_df = st.session_state.app_valid_df[st.session_state.app_valid_df['RecordId'] != orig_record_id]
                                
                                st.session_state[pending_delete_key] = None
                                st.success(t("msg_delete_success"))
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                    with cancel_col:
                        if st.button(
                            t("btn_cancel_delete"),
                            use_container_width=True,
                            key=f"main_btn_cancel_delete_{uid_safe}"
                        ):
                            st.session_state[pending_delete_key] = None
                            st.rerun()

    if not past_records.empty:
        st.markdown(f"### {t('records_past')}")
        for name, mode_groups in iter_records_grouped_by_name_and_mode(past_records):
            with st.expander(t("records_player_group", name=name), expanded=False):
                for mode, mode_records in mode_groups:
                    with st.expander(t("records_mode_group", mode=mode), expanded=False):
                        mode_records['TimestampDT'] = pd.to_datetime(mode_records['Timestamp'], errors='coerce')
                        if 'IsScratch' not in mode_records.columns:
                            mode_records['IsScratch'] = False

                        # Daily summary per mode under each player: date, total attempts, and fastest completed record.
                        daily_total_df = (
                            mode_records.groupby(['Date'], dropna=False)
                            .agg(
                                TotalCount=('Date', 'size'),
                                DnfCount=('IsScratch', lambda s: int(s.fillna(False).astype(bool).sum()))
                            )
                            .reset_index()
                        )
                        daily_total_df['DnfRate'] = daily_total_df.apply(
                            lambda row: (
                                float(row['DnfCount']) / float(row['TotalCount'])
                                if float(row['TotalCount']) > 0
                                else 0.0
                            ),
                            axis=1
                        )
                        daily_total_df['DnfRateDisplay'] = daily_total_df['DnfRate'].apply(lambda x: f"{x:.1%}")
                        daily_total_df['TotalDisplay'] = daily_total_df.apply(
                            lambda row: f"{int(row['TotalCount'])} (DNF: {int(row['DnfCount'])})",
                            axis=1
                        )
                        fastest_record_df = (
                            mode_records[
                                (~mode_records['IsScratch'])
                                & (mode_records['Time'].notnull())
                            ]
                            .sort_values(
                                by=['Date', 'Time', 'TimestampDT'],
                                ascending=[False, True, True],
                                na_position='last'
                            )
                            .drop_duplicates(subset=['Date'], keep='first')
                            .copy()
                        )
                        fastest_record_df['FastestCompletion'] = fastest_record_df['TimeDisplay'].fillna("-")

                        daily_summary_df = daily_total_df.merge(
                            fastest_record_df[['Date', 'FastestCompletion']],
                            on=['Date'],
                            how='left'
                        )
                        daily_summary_df['Date'] = daily_summary_df['Date'].fillna("-")
                        daily_summary_df['FastestCompletion'] = daily_summary_df['FastestCompletion'].fillna("-")
                        daily_summary_df = daily_summary_df.sort_values(
                            by=['Date'],
                            ascending=[False]
                        ).reset_index(drop=True)

                        display_df = daily_summary_df.rename(columns={
                            'Date': t("col_date"),
                            'TotalDisplay': t("col_total"),
                            'DnfRateDisplay': t("col_dnf_rate"),
                            'FastestCompletion': t("col_fastest")
                        })
                        st.dataframe(
                            display_df[[t("col_date"), t("col_total"), t("col_dnf_rate"), t("col_fastest")]],
                            hide_index=True,
                            width="stretch"
                        )
else:
    st.info(t("records_no_records"))
