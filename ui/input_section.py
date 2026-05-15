import uuid

import pandas as pd
import streamlit as st

from ui.decimal_input import decimal_input
from ui.toasts import queue_toast
from utils.app_config import AVAILABLE_MODES
from utils.data_manager import (
    format_cloud_error,
    get_current_timestamp,
    save_record_to_cloud,
    sync_temp_logs_to_cloud,
)
from utils.i18n import t
from utils.stats import get_personal_pb_rank


def render_input_section(conn, names):
    # Initialize temp logs pool and fast mode state
    if "temp_logs" not in st.session_state:
        st.session_state.temp_logs = []
    if "fast_mode" not in st.session_state:
        st.session_state.fast_mode = False

    if "last_name" not in st.session_state:
        st.session_state.last_name = names[0]
    if "last_mode" not in st.session_state:
        st.session_state.last_mode = AVAILABLE_MODES[0]
    if "selected_player" not in st.session_state:
        st.session_state.selected_player = st.session_state.last_name
    if "selected_mode" not in st.session_state:
        st.session_state.selected_mode = st.session_state.last_mode
    if "input_time" not in st.session_state:
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
        unsafe_allow_html=True,
    )
    with st.container(key="mode_cards_row"):
        mode_cols = st.columns(len(AVAILABLE_MODES))
        for idx, available_mode in enumerate(AVAILABLE_MODES):
            with mode_cols[idx]:
                clicked = st.button(
                    available_mode,
                    key=f"mode_card_{idx}",
                    use_container_width=True,
                    type="primary" if st.session_state.selected_mode == available_mode else "secondary",
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
    if "time_input_key" not in st.session_state:
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
                pending_valid_logs = [log for log in st.session_state.temp_logs if not log.get("IsScratch", False)]
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
                    "IsScratch": is_scratch,
                })
                queue_toast(t("msg_added", time=f"{time_val:.3f}"), icon="⏱️")
                if pb_rank is not None:
                    queue_toast(
                        t("msg_pb_rank", name=name, mode=mode, time=f"{time_val:.3f}", rank=pb_rank),
                        icon="🏆",
                    )

                st.session_state.last_name = name
                st.session_state.last_mode = mode
                st.session_state.time_input_key += 1
                st.rerun()
            else:
                # Immediate upload to cloud (original behavior)
                try:
                    record_id = save_record_to_cloud(conn, timestamp_str, name, mode, time_val, is_scratch)

                    new_row = {
                        "Timestamp": timestamp_str,
                        "Name": name,
                        "Mode": mode,
                        "Time": time_val,
                        "IsScratch": is_scratch,
                        "RecordId": record_id,
                    }
                    st.session_state.app_data_df = pd.concat(
                        [st.session_state.app_data_df, pd.DataFrame([new_row])],
                        ignore_index=True,
                    )
                    if not is_scratch:
                        st.session_state.app_valid_df = pd.concat(
                            [st.session_state.app_valid_df, pd.DataFrame([new_row])],
                            ignore_index=True,
                        )

                    if is_scratch:
                        st.warning(t("msg_dnf", name=name, mode=mode, time=time_val))
                    else:
                        st.success(t("msg_success", name=name, mode=mode, time=time_val))
                        if pb_rank is not None:
                            queue_toast(
                                t("msg_pb_rank", name=name, mode=mode, time=f"{time_val:.3f}", rank=pb_rank),
                                icon="🏆",
                            )

                    st.session_state.last_name = name
                    st.session_state.last_mode = mode
                    # Clear time input by incrementing the key (creates new input)
                    st.session_state.time_input_key += 1
                    st.rerun()
                except Exception as e:
                    st.error(t("err_save_fail", err=format_cloud_error(e)))

    # --- Temp Pool Display & Sync ---
    if st.session_state.temp_logs:
        st.divider()
        st.subheader(t("temp_pool"))
        if not st.session_state.fast_mode:
            st.caption(t("temp_pool_unsynced_note"))

        temp_df = pd.DataFrame(st.session_state.temp_logs)
        temp_df["TimeDisplay"] = temp_df.apply(
            lambda row: f"❌ {row['Time']:.3f}s" if row.get("IsScratch", False) else f"{row['Time']:.3f}s",
            axis=1,
        )
        st.dataframe(temp_df[["Name", "Mode", "TimeDisplay"]], hide_index=True, width="stretch")

        sync_col, clear_col = st.columns(2)
        with sync_col:
            if st.button(t("btn_sync"), type="primary", use_container_width=True):
                try:
                    with st.spinner(t("syncing")):
                        new_rows = []
                        for log in st.session_state.temp_logs:
                            synced_log = dict(log)
                            synced_log["RecordId"] = synced_log.get("RecordId") or str(uuid.uuid4())
                            new_rows.append(synced_log)

                        sync_temp_logs_to_cloud(conn, new_rows)

                        st.session_state.app_data_df = pd.concat(
                            [st.session_state.app_data_df, pd.DataFrame(new_rows)],
                            ignore_index=True,
                        )
                        valid_logs = [log for log in new_rows if not log.get("IsScratch", False)]
                        if valid_logs:
                            st.session_state.app_valid_df = pd.concat(
                                [st.session_state.app_valid_df, pd.DataFrame(valid_logs)],
                                ignore_index=True,
                            )

                        st.session_state.temp_logs = []
                        st.success(t("msg_synced"))
                        st.rerun()
                except Exception as e:
                    st.error(t("sync_fail", err=format_cloud_error(e)))

        with clear_col:
            if st.button(t("btn_clear"), use_container_width=True):
                st.session_state.temp_logs = []
                st.rerun()
