import streamlit as st

from ui.input_section import render_input_section
from ui.records_section import render_records_section
from ui.stats_section import render_stats_tabs
from ui.styles import apply_global_styles
from ui.toasts import flush_queued_toasts
from utils.data_manager import get_connection, load_data, load_goals, load_players
from utils.i18n import setup_language_selector, t

# Page configuration (responsive layout for mobile)
st.set_page_config(page_title="Stacking Tracker", layout="centered")

setup_language_selector()
apply_global_styles()

st.title("⏱️ Stacking Tracker")
st.markdown(t("subtitle"))
flush_queued_toasts()

conn = get_connection()

if "app_data_df" not in st.session_state or "app_valid_df" not in st.session_state:
    loaded_df, loaded_valid_df = load_data(conn)
    st.session_state.app_data_df = loaded_df.copy()
    st.session_state.app_valid_df = loaded_valid_df.copy()

df = st.session_state.app_data_df
valid_df = st.session_state.app_valid_df

default_names_from_data = (
    df["Name"].dropna().astype(str).str.strip().unique().tolist()
    if (not df.empty and "Name" in df.columns)
    else []
)
names = load_players(conn, default_names_from_data)
goals_df = load_goals(conn)

if "last_name" in st.session_state and st.session_state.last_name not in names:
    st.session_state.last_name = names[0]

st.sidebar.markdown("---")
if st.sidebar.button(t("btn_refresh"), use_container_width=True):
    st.cache_data.clear()
    for state_key in ("app_data_df", "app_valid_df"):
        if state_key in st.session_state:
            del st.session_state[state_key]
    st.rerun()

st.sidebar.toggle(
    t("toggle_backup_time_input"),
    key="show_backup_time_input",
    value=st.session_state.get("show_backup_time_input", False),
    help=t("toggle_backup_time_input_help"),
)

render_input_section(conn, names)

df = st.session_state.app_data_df
valid_df = st.session_state.app_valid_df
render_stats_tabs(df, valid_df, goals_df)
render_records_section(conn, df)
