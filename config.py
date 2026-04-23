import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(i) for i in os.getenv("ADMIN_IDS", "").split(",") if i.strip()]
CARD_NUMBER = os.getenv("CARD_NUMBER", "")
CARD_OWNER = os.getenv("CARD_OWNER", "")
BOT_USERNAME = os.getenv("BOT_USERNAME", "")
DB_PATH = "bot.db"

USE_REDIS = os.getenv("USE_REDIS", "false").lower() == "true"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# AI Agent config
AI_ENABLED = os.getenv("AI_ENABLED", "false").lower() == "true"
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini")
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "gemini-2.0-flash")

# Referral bonus config
BONUS_JOIN = {
    "bronze": int(os.getenv("BONUS_JOIN_BRONZE", 5000)),
    "silver": int(os.getenv("BONUS_JOIN_SILVER", 8000)),
    "gold":   int(os.getenv("BONUS_JOIN_GOLD", 12000)),
}
BONUS_ORDER_PCT = {
    "bronze": int(os.getenv("BONUS_ORDER_BRONZE", 5)),
    "silver": int(os.getenv("BONUS_ORDER_SILVER", 8)),
    "gold":   int(os.getenv("BONUS_ORDER_GOLD", 12)),
}
TIER_THRESHOLDS = {"silver": 15, "gold": 30}  # min referral count


def get_tier(ref_count: int) -> str:
    if ref_count >= TIER_THRESHOLDS["gold"]:
        return "gold"
    if ref_count >= TIER_THRESHOLDS["silver"]:
        return "silver"
    return "bronze"


TIER_LABELS = {
    "bronze": {"uz": "🥉 Bronza", "ru": "🥉 Бронза"},
    "silver": {"uz": "🥈 Kumush", "ru": "🥈 Серебро"},
    "gold":   {"uz": "🥇 Oltin",  "ru": "🥇 Золото"},
}
