from datetime import datetime

import pandas as pd
import streamlit as st

from utils.app_config import TIMEZONE
from utils.data_manager import delete_record_from_cloud, update_record_in_cloud
from utils.i18n import t
from utils.stats import iter_records_grouped_by_name_and_mode


def format_record(row):
    ts = str(row.get("Timestamp", ""))
    time_part = ts[11:19] if len(ts) >= 19 else ts
    if pd.notnull(row.get("Time")):
        time_text = f"{float(row['Time']):.3f}s"
    else:
        time_text = "-"
    display_time = f"❌ {time_text} (Scratch)" if row.get("IsScratch", False) else time_text
    return f"{time_part} | {row['Name']} | {row['Mode']} | {display_time}"


def render_records_section(conn, df):
    st.divider()
    st.subheader(t("records_header"))
    if df.empty:
        st.info(t("records_no_records"))
        return

    today_str = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    recent_df = df.sort_values(by="Timestamp", ascending=False).head(500).copy()
    recent_df["Date"] = pd.to_datetime(recent_df["Timestamp"], errors="coerce").dt.strftime("%Y-%m-%d")
    recent_df["TimeDisplay"] = recent_df.apply(
        lambda row: f"❌ {float(row['Time']):.3f}s (Scratch)" if row.get("IsScratch", False) and pd.notnull(row["Time"])
        else (f"{float(row['Time']):.3f}s" if pd.notnull(row["Time"]) else "-"),
        axis=1,
    )

    today_records = recent_df[recent_df["Date"] == today_str].copy()
    past_records = recent_df[recent_df["Date"] != today_str].copy()

    _render_today_records(conn, today_records, today_str)
    _render_past_records(past_records)


def _render_today_records(conn, today_records, today_str):
    if today_records.empty:
        return

    st.markdown(f"### {t('records_today', date=today_str)}")
    for name, mode_groups in iter_records_grouped_by_name_and_mode(today_records):
        with st.expander(t("records_player_group", name=name), expanded=False):
            for mode, mode_records in mode_groups:
                with st.expander(t("records_mode_group", mode=mode), expanded=False):
                    st.dataframe(
                        mode_records[["Timestamp", "Name", "TimeDisplay"]],
                        hide_index=True,
                        width="stretch",
                    )

    st.write("")
    with st.expander(t("records_edit_header"), expanded=False):
        _render_record_editor(conn, today_records)


def _render_record_editor(conn, today_records):
    edit_options = today_records.copy()
    if edit_options.empty:
        st.info(t("records_edit_empty"))
        return

    pending_delete_key = "main_pending_delete_uid"
    edit_options["UID"] = edit_options["RecordId"].astype(str)
    uid_to_display = dict(zip(edit_options["UID"], edit_options.apply(format_record, axis=1)))

    selected_uid = st.selectbox(
        t("edit_select_record"),
        options=edit_options["UID"].tolist(),
        format_func=lambda uid: uid_to_display[uid],
        key="main_edit_record_select",
    )

    selected_row = edit_options[edit_options["UID"] == selected_uid].iloc[0]
    uid_safe = selected_uid.replace("|", "_")
    orig_ts = selected_row["Timestamp"]
    orig_name = selected_row["Name"]
    orig_mode = selected_row["Mode"]
    orig_record_id = str(selected_row.get("RecordId", ""))
    orig_time = float(selected_row["Time"]) if pd.notnull(selected_row["Time"]) else 0.0
    orig_scratch = bool(selected_row.get("IsScratch", False))

    new_time_val = st.number_input(
        t("edit_time"),
        min_value=0.0,
        value=float(orig_time),
        step=0.001,
        format="%.3f",
        key=f"main_edit_time_input_{uid_safe}",
    )
    new_scratch = st.checkbox(
        t("edit_dnf"),
        value=orig_scratch,
        key=f"main_edit_dnf_{uid_safe}",
    )

    col_u, col_d = st.columns(2)
    with col_u:
        if st.button(t("btn_update"), use_container_width=True, type="primary", key="main_btn_update"):
            _update_selected_record(conn, orig_ts, orig_name, orig_mode, orig_record_id, new_time_val, new_scratch)

    with col_d:
        if st.button(t("btn_delete"), use_container_width=True, key="main_btn_delete"):
            st.session_state[pending_delete_key] = selected_uid

    if st.session_state.get(pending_delete_key) == selected_uid:
        _render_delete_confirmation(conn, pending_delete_key, selected_uid, uid_safe, orig_ts, orig_name, orig_mode, orig_record_id)


def _update_selected_record(conn, orig_ts, orig_name, orig_mode, orig_record_id, new_time_val, new_scratch):
    if new_time_val is None or new_time_val <= 0:
        st.error(t("err_invalid_time"))
        return

    try:
        update_record_in_cloud(
            conn,
            orig_ts,
            orig_name,
            orig_mode,
            new_time_val,
            new_scratch,
            record_id=orig_record_id,
        )

        mask = st.session_state.app_data_df["RecordId"] == orig_record_id
        st.session_state.app_data_df.loc[mask, "Time"] = new_time_val
        st.session_state.app_data_df.loc[mask, "IsScratch"] = new_scratch

        st.session_state.app_valid_df = st.session_state.app_data_df[
            (st.session_state.app_data_df["Time"].notnull()) & (~st.session_state.app_data_df["IsScratch"])
        ]

        st.success(t("msg_update_success"))
        st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")


def _render_delete_confirmation(conn, pending_delete_key, selected_uid, uid_safe, orig_ts, orig_name, orig_mode, orig_record_id):
    st.warning(t("delete_confirm_prompt"))
    confirm_col, cancel_col = st.columns(2)
    with confirm_col:
        if st.button(
            t("btn_confirm_delete"),
            use_container_width=True,
            type="primary",
            key=f"main_btn_confirm_delete_{uid_safe}",
        ):
            _delete_selected_record(conn, pending_delete_key, orig_ts, orig_name, orig_mode, orig_record_id)
    with cancel_col:
        if st.button(
            t("btn_cancel_delete"),
            use_container_width=True,
            key=f"main_btn_cancel_delete_{uid_safe}",
        ):
            st.session_state[pending_delete_key] = None
            st.rerun()


def _delete_selected_record(conn, pending_delete_key, orig_ts, orig_name, orig_mode, orig_record_id):
    try:
        delete_record_from_cloud(
            conn,
            orig_ts,
            orig_name,
            orig_mode,
            record_id=orig_record_id,
        )

        st.session_state.app_data_df = st.session_state.app_data_df[
            st.session_state.app_data_df["RecordId"] != orig_record_id
        ]
        st.session_state.app_valid_df = st.session_state.app_valid_df[
            st.session_state.app_valid_df["RecordId"] != orig_record_id
        ]

        st.session_state[pending_delete_key] = None
        st.success(t("msg_delete_success"))
        st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")


def _render_past_records(past_records):
    if past_records.empty:
        return

    st.markdown(f"### {t('records_past')}")
    for name, mode_groups in iter_records_grouped_by_name_and_mode(past_records):
        with st.expander(t("records_player_group", name=name), expanded=False):
            for mode, mode_records in mode_groups:
                with st.expander(t("records_mode_group", mode=mode), expanded=False):
                    _render_past_mode_summary(mode_records)


def _render_past_mode_summary(mode_records):
    mode_records["TimestampDT"] = pd.to_datetime(mode_records["Timestamp"], errors="coerce")
    if "IsScratch" not in mode_records.columns:
        mode_records["IsScratch"] = False

    daily_total_df = (
        mode_records.groupby(["Date"], dropna=False)
        .agg(
            TotalCount=("Date", "size"),
            DnfCount=("IsScratch", lambda s: int(s.fillna(False).astype(bool).sum())),
        )
        .reset_index()
    )
    daily_total_df["DnfRate"] = daily_total_df.apply(
        lambda row: (
            float(row["DnfCount"]) / float(row["TotalCount"])
            if float(row["TotalCount"]) > 0
            else 0.0
        ),
        axis=1,
    )
    daily_total_df["DnfRateDisplay"] = daily_total_df["DnfRate"].apply(lambda x: f"{x:.1%}")
    daily_total_df["TotalDisplay"] = daily_total_df.apply(
        lambda row: f"{int(row['TotalCount'])} (Scratch: {int(row['DnfCount'])})",
        axis=1,
    )
    fastest_record_df = (
        mode_records[
            (~mode_records["IsScratch"])
            & (mode_records["Time"].notnull())
        ]
        .sort_values(
            by=["Date", "Time", "TimestampDT"],
            ascending=[False, True, True],
            na_position="last",
        )
        .drop_duplicates(subset=["Date"], keep="first")
        .copy()
    )
    fastest_record_df["FastestCompletion"] = fastest_record_df["TimeDisplay"].fillna("-")

    daily_summary_df = daily_total_df.merge(
        fastest_record_df[["Date", "FastestCompletion"]],
        on=["Date"],
        how="left",
    )
    daily_summary_df["Date"] = daily_summary_df["Date"].fillna("-")
    daily_summary_df["FastestCompletion"] = daily_summary_df["FastestCompletion"].fillna("-")
    daily_summary_df = daily_summary_df.sort_values(
        by=["Date"],
        ascending=[False],
    ).reset_index(drop=True)

    display_df = daily_summary_df.rename(columns={
        "Date": t("col_date"),
        "TotalDisplay": t("col_total"),
        "DnfRateDisplay": t("col_dnf_rate"),
        "FastestCompletion": t("col_fastest"),
    })
    st.dataframe(
        display_df[[t("col_date"), t("col_total"), t("col_dnf_rate"), t("col_fastest")]],
        hide_index=True,
        width="stretch",
    )
