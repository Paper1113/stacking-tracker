import streamlit as st


def queue_toast(message: str, icon: str = "ℹ️"):
    if "pending_toasts" not in st.session_state:
        st.session_state.pending_toasts = []
    st.session_state.pending_toasts.append({"message": message, "icon": icon})


def flush_queued_toasts():
    pending_toasts = st.session_state.pop("pending_toasts", [])
    for toast in pending_toasts:
        st.toast(toast.get("message", ""), icon=toast.get("icon", "ℹ️"))
