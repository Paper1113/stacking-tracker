import json
import os
from zoneinfo import ZoneInfo

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIMEZONE = ZoneInfo("Asia/Hong_Kong")

with open(os.path.join(PROJECT_ROOT, "config.json"), "r", encoding="utf-8") as f:
    config = json.load(f)

AVAILABLE_MODES = config.get("AVAILABLE_MODES", [])
DEFAULT_PLAYERS = config.get("DEFAULT_PLAYERS", [])
DATA_TTL = config.get("DATA_TTL", 300)

with open(os.path.join(PROJECT_ROOT, "i18n.json"), "r", encoding="utf-8") as f:
    TRANSLATIONS = json.load(f)
