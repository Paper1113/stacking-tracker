import streamlit as st
import streamlit.components.v1 as components
import json
import os

# Get absolute path to the project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load configuration
with open(os.path.join(PROJECT_ROOT, "config.json"), "r", encoding="utf-8") as f:
    config = json.load(f)

AVAILABLE_MODES = config.get("AVAILABLE_MODES", [])
DEFAULT_PLAYERS = config.get("DEFAULT_PLAYERS", [])
DATA_TTL = config.get("DATA_TTL", 300)

# Load translations
with open(os.path.join(PROJECT_ROOT, "i18n.json"), "r", encoding="utf-8") as f:
    TRANSLATIONS = json.load(f)

def t(key, **kwargs):
    """Get translated string for the current language."""
    text = TRANSLATIONS.get(st.session_state.lang, TRANSLATIONS["zh-TW"]).get(key, key)
    return text.format(**kwargs) if kwargs else text



def setup_language_selector():
    """Injects JS language detection and sets up sidebar selection."""
    if 'lang_detected' not in st.session_state:
        st.session_state.lang_detected = False
    if 'lang' not in st.session_state:
        st.session_state.lang = "zh-TW"  # Default to Traditional Chinese

    # Inject JS to detect browser language (only on first load)
    if not st.session_state.lang_detected:
        components.html("""
        <script>
        const lang = navigator.language || navigator.userLanguage || 'zh-TW';
        const isZh = lang.startsWith('zh');
        // Send result to Streamlit via query params workaround
        window.parent.postMessage({type: 'streamlit:setComponentValue', value: isZh ? 'zh-TW' : 'en'}, '*');
        </script>
        """, height=0)
        st.session_state.lang_detected = True

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
