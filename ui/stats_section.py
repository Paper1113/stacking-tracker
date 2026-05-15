import pandas as pd
import streamlit as st

from utils.i18n import t
from utils.stats import (
    DAILY_PROGRESS_COLUMNS,
    prepare_ao5_data,
    prepare_daily_best_data,
    prepare_daily_progress_data,
    prepare_today_top5_data,
    prepare_top_pb_attempts,
)


def render_stats_tabs(df, valid_df, goals_df):
    valid_df_sorted = valid_df.sort_values(by="Timestamp") if not valid_df.empty else pd.DataFrame()

    ao5_df = prepare_ao5_data(valid_df_sorted)
    pb_df = prepare_daily_best_data(valid_df)
    progress_df = prepare_daily_progress_data(df, goals_df)
    today_top5_df = prepare_today_top5_data(df)

    tab_daily, tab_today_top5, tab_ao5, tab_pb = st.tabs([
        t("daily_header"),
        t("today_top5_header"),
        t("ao5_header"),
        t("pb_header"),
    ])

    with tab_daily:
        _render_daily_tab(df, goals_df, progress_df)

    with tab_today_top5:
        _render_today_top5_tab(today_top5_df)

    with tab_ao5:
        _render_ao5_tab(ao5_df)

    with tab_pb:
        _render_pb_tab(pb_df, valid_df)


def _render_daily_tab(df, goals_df, progress_df):
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
        for p_name in sorted(progress_df["Name"].unique()):
            with st.expander(t("daily_expander", name=p_name), expanded=True):
                p_df = progress_df[progress_df["Name"] == p_name].reset_index(drop=True)
                display_df = p_df.drop(columns=["Name"]).rename(columns=progress_display_columns)
                st.dataframe(display_df[progress_display_order], hide_index=True, width="stretch")
    else:
        if df.empty:
            st.info(t("daily_no_records"))
        elif goals_df.empty:
            st.info(t("daily_no_goals_sheet"))
        else:
            st.info(t("daily_no_goals_match"))


def _render_today_top5_tab(today_top5_df):
    if not today_top5_df.empty:
        st.caption(t("today_top5_desc"))
        for p_name in sorted(today_top5_df["Name"].dropna().unique()):
            with st.expander(t("records_player_group", name=p_name), expanded=False):
                p_top5_df = today_top5_df[today_top5_df["Name"] == p_name].copy()
                for mode in sorted(p_top5_df["Mode"].dropna().unique()):
                    with st.expander(t("records_mode_group", mode=mode), expanded=False):
                        pm_top5_df = p_top5_df[p_top5_df["Mode"] == mode].copy().sort_values(by="Rank")
                        pm_top5_df["Time"] = pm_top5_df["Time"].map("{:,.3f}s".format)
                        pm_top5_df["Gap"] = pm_top5_df["Gap"].map(
                            lambda x: "" if pd.isna(x) or x == 0 else f"+{x:.3f}s"
                        )
                        pm_top5_df["Timestamp"] = pd.to_datetime(
                            pm_top5_df["Timestamp"], errors="coerce"
                        ).dt.strftime("%H:%M:%S").fillna("-")
                        display_df = pm_top5_df.rename(columns={
                            "Rank": t("col_rank"),
                            "Time": t("col_time"),
                            "Gap": t("col_gap"),
                            "Timestamp": t("col_timestamp"),
                        })
                        st.dataframe(
                            display_df[[t("col_rank"), t("col_time"), t("col_gap"), t("col_timestamp")]],
                            hide_index=True,
                            width="stretch",
                        )
    else:
        st.info(t("today_top5_no_records"))


def _render_ao5_tab(ao5_df):
    if not ao5_df.empty:
        ao5_df["Ao5"] = ao5_df["Ao5"].map("{:,.3f}s".format)
        st.markdown(t("ao5_desc"))
        for mode in sorted(ao5_df["Mode"].unique()):
            st.subheader(t("ao5_mode", mode=mode))
            mode_ao5_df = ao5_df[ao5_df["Mode"] == mode].sort_values(by="Name").reset_index(drop=True)
            st.dataframe(mode_ao5_df[["Name", "Ao5"]], hide_index=True, width="stretch")
    else:
        st.write(t("ao5_need5"))


def _render_pb_tab(pb_df, valid_df):
    if not pb_df.empty:
        for p_name in sorted(pb_df["Name"].dropna().unique()):
            with st.expander(t("pb_player_group", name=p_name), expanded=False):
                p_pb_df = pb_df[pb_df["Name"] == p_name].copy()
                for mode in sorted(p_pb_df["Mode"].dropna().unique()):
                    with st.expander(t("pb_mode", mode=mode), expanded=False):
                        pm_df = p_pb_df[p_pb_df["Mode"] == mode].copy()
                        chart_data = pm_df.sort_values(by="Date")[["Date", "Time"]].set_index("Date")

                        st.line_chart(chart_data)

                        pb_attempts_df = prepare_top_pb_attempts(valid_df, p_name, mode)
                        if not pb_attempts_df.empty:
                            display_df = pb_attempts_df.copy()
                            display_df["Time"] = display_df["Time"].map("{:,.3f}s".format)
                            display_df["Gap"] = display_df["Gap"].map(
                                lambda x: "" if pd.isna(x) or x == 0 else f"+{x:.3f}s"
                            )
                            display_df = display_df.rename(columns={
                                "Rank": t("col_rank"),
                                "Time": t("col_time"),
                                "Gap": t("col_gap"),
                                "Date": t("col_date"),
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
