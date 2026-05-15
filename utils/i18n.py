import streamlit as st
from utils.app_config import TRANSLATIONS

def t(key, **kwargs):
    """Get translated string for the current language."""
    lang = st.session_state.get("lang", "zh-TW")
    text = TRANSLATIONS.get(lang, TRANSLATIONS["zh-TW"]).get(key, key)
    return text.format(**kwargs) if kwargs else text

def _detect_browser_language():
    """
    Detect browser language from request headers.
    Returns 'zh-TW' for Chinese locales, otherwise 'en'.
    """
    try:
        headers = getattr(st.context, "headers", {}) or {}
        accept_lang = headers.get("Accept-Language") or headers.get("accept-language") or ""
        normalized = str(accept_lang).strip().lower()
        if normalized.startswith("zh") or ",zh" in normalized:
            return "zh-TW"
        if normalized:
            return "en"
    except Exception:
        pass
    return "zh-TW"

def setup_language_selector():
    """Set up language using browser detection on first load + manual override selector."""
    if 'lang' not in st.session_state:
        st.session_state.lang = _detect_browser_language()

    # Language selector in sidebar
    LANG_OPTIONS = {"繁體中文": "zh-TW", "English": "en"}
    LANG_LABELS = list(LANG_OPTIONS.keys())
    current_lang_idx = LANG_LABELS.index("繁體中文") if st.session_state.lang == "zh-TW" else LANG_LABELS.index("English")

    selected_lang_label = st.sidebar.selectbox(
        "🌐 語言 / Language",
        LANG_LABELS,
        index=current_lang_idx,
        key="lang_selector"
    )
    st.session_state.lang = LANG_OPTIONS[selected_lang_label]
