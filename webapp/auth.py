"""
Telegram Mini App initData verification.

Verifies the HMAC-SHA256 signature sent by Telegram WebApp to ensure
the request is genuinely from a Telegram user and hasn't been tampered with.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qs, unquote

from fastapi import Header, HTTPException

from config import BOT_TOKEN

# How long (seconds) an initData signature stays valid
INIT_DATA_MAX_AGE = 86400  # 24 hours


def _validate_init_data(init_data: str, bot_token: str) -> dict:
    """
    Validate Telegram WebApp initData and return the parsed user dict.

    Raises ValueError on any validation failure.
    """
    if not init_data:
        raise ValueError("Empty initData")

    parsed = parse_qs(init_data, keep_blank_values=True)

    # Extract and remove hash
    received_hash = parsed.pop("hash", [None])[0]
    if not received_hash:
        raise ValueError("Missing hash in initData")

    # Build check string: sorted key=value pairs joined by \n
    data_pairs = []
    for key in sorted(parsed.keys()):
        val = parsed[key][0]
        data_pairs.append(f"{key}={val}")
    data_check_string = "\n".join(data_pairs)

    # Compute HMAC
    secret_key = hmac.new(
        b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256
    ).digest()
    computed_hash = hmac.new(
        secret_key, data_check_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise ValueError("Invalid initData signature")

    # Check auth_date freshness
    auth_date_str = parsed.get("auth_date", [None])[0]
    if auth_date_str:
        try:
            auth_date = int(auth_date_str)
            if time.time() - auth_date > INIT_DATA_MAX_AGE:
                raise ValueError("initData expired")
        except (ValueError, TypeError):
            pass

    # Parse user JSON
    user_str = parsed.get("user", [None])[0]
    if not user_str:
        raise ValueError("No user in initData")

    try:
        user = json.loads(unquote(user_str))
    except (json.JSONDecodeError, TypeError):
        raise ValueError("Invalid user JSON in initData")

    return user


async def get_current_user(
    x_telegram_init_data: str = Header(None, alias="X-Telegram-Init-Data"),
) -> dict:
    """
    FastAPI dependency that extracts and verifies the Telegram user
    from the X-Telegram-Init-Data header.

    Returns the user dict with at least {"id": int, ...}.
    Raises HTTP 401 if verification fails.
    """
    if not x_telegram_init_data:
        raise HTTPException(status_code=401, detail="Missing X-Telegram-Init-Data header")

    try:
        user = _validate_init_data(x_telegram_init_data, BOT_TOKEN)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Auth failed: {e}")

    if "id" not in user:
        raise HTTPException(status_code=401, detail="No user id in initData")

    return user
