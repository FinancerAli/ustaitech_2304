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


def _normalize_service(row: Any, avg_rating: float = 0.0, review_count: int = 0) -> dict[str, Any]:
    data = _row_to_dict(row)

    return {
        "id": data.get("id"),
        "name": data.get("name"),
        "description": data.get("description") or "",
        "description_ru": data.get("description_ru") or "",
        "price": data.get("price"),
        "stock": data.get("stock"),
        "active": bool(data.get("active", 1)),
        "category_id": data.get("category_id"),
        "image_file_id": data.get("image_file_id"),
        "delivery_content": data.get("delivery_content"),
        "promo_cashback_percent": data.get("cashback_percent"),
        "promo_title": data.get("promo_title"),
        "promo_active": bool(data.get("promo_active", 0)),
        "avg_rating": avg_rating,
        "review_count": review_count,
    }


async def list_services(
    *,
    only_active: bool = True,
    category_id: int | None = None,
    query: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, Any]]:
    rows = await db.get_services(
        only_active=only_active,
        category_id=category_id,
        query=query,
        limit=limit,
        offset=offset,
    )

    result: list[dict[str, Any]] = []
    for row in rows:
        service_id = row["id"]
        avg_rating, review_count = await db.get_service_avg_rating(service_id)
        result.append(
            _normalize_service(
                row,
                avg_rating=avg_rating,
                review_count=review_count,
            )
        )

    return result


async def get_service_detail(service_id: int) -> dict[str, Any] | None:
    row = await db.get_service(service_id)
    if not row:
        return None

    avg_rating, review_count = await db.get_service_avg_rating(service_id)
    return _normalize_service(
        row,
        avg_rating=avg_rating,
        review_count=review_count,
    )


async def list_active_promotions() -> list[dict[str, Any]]:
    rows = await db.get_active_service_promotions()
    result: list[dict[str, Any]] = []

    for row in rows:
        data = _row_to_dict(row)
        result.append(
            {
                "id": data.get("id"),
                "service_id": data.get("service_id"),
                "service_name": data.get("service_name"),
                "service_price": data.get("price"),
                "title": data.get("title"),
                "cashback_percent": data.get("cashback_percent"),
                "is_active": bool(data.get("is_active", 0)),
                "starts_at": data.get("starts_at"),
                "ends_at": data.get("ends_at"),
            }
        )

    return result
