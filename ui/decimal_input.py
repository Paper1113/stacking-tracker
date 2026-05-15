import os

import streamlit as st
import streamlit.components.v1 as components

from utils.i18n import t

_decimal_input_func = components.declare_component(
    "decimal_input",
    path=os.path.join(os.path.dirname(os.path.dirname(__file__)), "decimal_input"),
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

    if component_value is not None and component_value > 0:
        return component_value
    return fallback_value if fallback_value > 0 else None
