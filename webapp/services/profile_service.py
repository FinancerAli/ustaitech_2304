from __future__ import annotations

from typing import Any

import database as db


def _row_to_dict(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    try:
        return dict(row)
    except Exception:
        if hasattr(row, "keys"):
            return {key: row[key] for key in row.keys()}
        raise


async def get_profile_summary(user_id: int) -> dict[str, Any] | None:
    user_row = await db.get_user(user_id)
    if not user_row:
        return None

    user = _row_to_dict(user_row)
    confirmed_row = await db.get_confirmed_customer_detail(user_id)

    if confirmed_row:
        confirmed = _row_to_dict(confirmed_row)
        return {
            "id": confirmed.get("id", user.get("id")),
            "username": confirmed.get("username", user.get("username")),
            "full_name": confirmed.get("full_name", user.get("full_name")),
            "bonus_balance": confirmed.get("bonus_balance", user.get("bonus_balance", 0)),
            "confirmed_orders_count": confirmed.get("confirmed_orders_count", 0),
            "total_spent": confirmed.get("total_spent", 0),
            "last_confirmed_at": confirmed.get("last_confirmed_at"),
            "last_order_id": confirmed.get("last_order_id"),
            "last_service_name": confirmed.get("last_service_name"),
            "is_confirmed_customer": True,
        }

    total_spent = await db.get_user_total_spent(user_id)
    confirmed_orders_count = await db.get_user_confirmed_orders_count(user_id)

    return {
        "id": user.get("id"),
        "username": user.get("username"),
        "full_name": user.get("full_name"),
        "bonus_balance": user.get("bonus_balance", 0),
        "confirmed_orders_count": confirmed_orders_count,
        "total_spent": total_spent,
        "last_confirmed_at": None,
        "last_order_id": None,
        "last_service_name": None,
        "is_confirmed_customer": confirmed_orders_count > 0,
    }


async def list_user_orders(user_id: int) -> list[dict[str, Any]]:
    rows = await db.get_user_orders(user_id)
    return [_row_to_dict(row) for row in rows]
