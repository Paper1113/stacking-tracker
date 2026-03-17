import streamlit as st
import pandas as pd
from datetime import datetime
import os
import streamlit.components.v1 as components

from utils.i18n import t, setup_language_selector, AVAILABLE_MODES
from utils.data_manager import (
    get_connection, load_data, load_players, load_goals,
    get_current_timestamp, save_record_to_cloud, sync_temp_logs_to_cloud,
    TIMEZONE
)
from utils.stats import prepare_ao5_data, prepare_pb_data, prepare_daily_progress_data

_decimal_input_func = components.declare_component(
    "decimal_input",
    path=os.path.join(os.path.dirname(__file__), "decimal_input")
)

def decimal_input(key=None, value=None):
    return _decimal_input_func(key=key, default=value)

# Page configuration (responsive layout for mobile)
st.set_page_config(page_title="Stacking Tracker", layout="centered")

# --- Language Setup ---
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
        for m in sorted(pb_df['Mode'].unique()):
            st.subheader(t("pb_mode", mode=m))
            m_df = pb_df[pb_df['Mode'] == m].sort_values(by='Name').reset_index(drop=True)
            st.dataframe(m_df[['Name', 'Time', 'Date']], hide_index=True, width="stretch")
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
                st.dataframe(grouped_by_date[[t('col_date'), t('col_total'), 'DNF', t('col_fastest'), t('col_players')]], hide_index=True, width="stretch")