import streamlit as st

# Check secrets for use_firestore flag (default to False for Google Sheets)
# Add this line to .streamlit/secrets.toml to test Firestore:
# use_firestore = true
USE_FIRESTORE = st.secrets.get("use_firestore", False)

if USE_FIRESTORE:
    from utils.data_manager_firestore import *
else:
    from utils.data_manager_gsheets import *
