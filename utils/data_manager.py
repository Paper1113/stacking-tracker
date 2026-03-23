import streamlit as st

USE_FIRESTORE = False
try:
    USE_FIRESTORE = st.secrets.get("use_firestore", False)
except Exception:
    pass

if USE_FIRESTORE:
    from utils.data_manager_firestore import *
else:
    from utils.data_manager_gsheets import *
