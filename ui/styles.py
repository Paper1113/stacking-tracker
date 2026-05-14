import streamlit as st

STREAMLIT_CSS_TARGET_VERSION = "1.55.0"


def apply_global_styles():
    # These selectors are verified against the pinned Streamlit version above.
    # Re-run a visual smoke test before changing Streamlit versions.
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
