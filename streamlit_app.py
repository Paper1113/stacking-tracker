import streamlit as st
import pandas as pd
from datetime import datetime
import os
import streamlit.components.v1 as components

from utils.i18n import t, setup_language_selector, AVAILABLE_MODES
from utils.data_manager import (
    get_connection, load_data, load_players, load_goals,
    get_current_timestamp, save_record_to_cloud, sync_temp_logs_to_cloud,
    update_record_in_cloud, delete_record_from_cloud,
    TIMEZONE
)
from utils.stats import prepare_ao5_data, prepare_pb_data, prepare_daily_progress_data

_decimal_input_func = components.declare_component(
    "decimal_input",
    path=os.path.join(os.path.dirname(__file__), "decimal_input")
)

def decimal_input(key=None, value=None):
    return _decimal_input_func(key=key, default=value, value=value)

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

# --- Data Loading ---
conn = get_connection()
df, valid_df = load_data(conn)

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
    st.rerun()


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
                st.toast(t("msg_added", time=f"{time_val:.3f}"), icon="⏱️")
                
                st.session_state.last_name = name
                st.session_state.last_mode = mode
                st.session_state.time_input_key += 1
                st.rerun()
            else:
                # Immediate upload to cloud (original behavior)
                try:
                    save_record_to_cloud(conn, timestamp_str, name, mode, time_val, is_scratch)

                    if is_scratch:
                        st.warning(t("msg_dnf", name=name, mode=mode, time=time_val))
                    else:
                        st.success(t("msg_success", name=name, mode=mode, time=time_val))

                    st.cache_data.clear()
                    
                    st.session_state.last_name = name
                    st.session_state.last_mode = mode
                    # Clear time input by incrementing the key (creates new input)
                    st.session_state.time_input_key += 1
                    st.rerun()
                except Exception as e:
                    st.error(t("err_save_fail", err=e))

    # --- Temp Pool Display & Sync (only when fast mode is used) ---
    if st.session_state.temp_logs and st.session_state.fast_mode:
        st.divider()
        st.subheader(t("temp_pool"))

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
                        sync_temp_logs_to_cloud(conn, st.session_state.temp_logs)

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
valid_df_sorted = valid_df.sort_values(by='Timestamp') if not valid_df.empty else pd.DataFrame()

ao5_df = prepare_ao5_data(valid_df_sorted)
pb_df = prepare_pb_data(valid_df)
progress_df = prepare_daily_progress_data(df, goals_df)

# Create tabs for stats
tab_daily, tab_ao5, tab_pb = st.tabs([t("daily_header"), t("ao5_header"), t("pb_header")])

with tab_daily:
    if not progress_df.empty:
        for p_name in sorted(progress_df['Name'].unique()):
            with st.expander(t("daily_expander", name=p_name), expanded=True):
                p_df = progress_df[progress_df['Name'] == p_name].reset_index(drop=True)
                st.dataframe(p_df.drop(columns=['Name']), hide_index=True, width="stretch")
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
            st.dataframe(m_ao5_df[['Name', 'Ao5']], hide_index=True, width="stretch")
    else:
        st.write(t("ao5_need5"))

with tab_pb:
    if not pb_df.empty:
        # Convert to Plotly-ready or Streamlit-ready format
        # We need a dataframe where index is Date, columns are Players, values are Times
        for m in sorted(pb_df['Mode'].unique()):
            with st.expander(t("pb_mode", mode=m), expanded=False):
                m_df = pb_df[pb_df['Mode'] == m].copy()

                # Pivot the data for line chart: Date as index, Names as columns
                chart_data = m_df.pivot(index='Date', columns='Name', values='Time')

                # Show the trend chart
                st.line_chart(chart_data)

                # Show per-person Top 5 PB tables below the chart
                st.markdown("##### 🏆 Top 5 PB (Per Player)")
                rank_df = valid_df[valid_df['Mode'] == m].copy()
                if not rank_df.empty:
                    rank_df['Date'] = pd.to_datetime(rank_df['Timestamp'], errors='coerce').dt.strftime('%Y-%m-%d')
                    for p_name in sorted(rank_df['Name'].unique()):
                        p_df = rank_df[rank_df['Name'] == p_name].sort_values(by='Time').head(5).reset_index(drop=True)
                        if p_df.empty:
                            continue
                        p_df.insert(0, "Rank", range(1, len(p_df) + 1))

                        # Safely format Time column
                        p_df['Time'] = p_df['Time'].apply(
                            lambda x: f"{float(x):.3f}s" if pd.notnull(x) and str(x).replace('.', '', 1).isdigit() else str(x)
                        )

                        st.markdown(f"**{p_name}**")
                        st.dataframe(p_df[['Rank', 'Time', 'Date']], hide_index=True, width="stretch")
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
        for mode in sorted(today_records['Mode'].dropna().unique()):
            mode_records = today_records[today_records['Mode'] == mode].copy().reset_index(drop=True)
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
                def format_record(row):
                    ts = str(row.get('Timestamp', ''))
                    time_part = ts[11:19] if len(ts) >= 19 else ts
                    if pd.notnull(row.get('Time')):
                        time_text = f"{float(row['Time']):.3f}s"
                    else:
                        time_text = "-"
                    display_time = f"❌ {time_text} (DNF)" if row.get('IsScratch', False) else time_text
                    return f"{time_part} | {row['Name']} | {row['Mode']} | {display_time}"

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
                                st.success(t("msg_update_success"))
                                st.cache_data.clear()
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
                                st.session_state[pending_delete_key] = None
                                st.success(t("msg_delete_success"))
                                st.cache_data.clear()
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
        for mode in sorted(past_records['Mode'].dropna().unique()):
            mode_records = past_records[past_records['Mode'] == mode].copy().reset_index(drop=True)
            with st.expander(t("records_mode_group", mode=mode), expanded=False):
                st.dataframe(
                    mode_records[['Timestamp', 'Name', 'TimeDisplay']],
                    hide_index=True,
                    width="stretch"
                )
else:
    st.info(t("records_no_records"))
