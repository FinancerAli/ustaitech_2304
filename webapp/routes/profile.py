from __future__ import annotations

from fastapi import APIRouter, HTTPException

from webapp.services.profile_service import get_profile_summary, list_user_orders

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/{user_id}/summary")
async def get_profile_summary_route(user_id: int):
    item = await get_profile_summary(user_id)
    if not item:
        raise HTTPException(status_code=404, detail="User not found")
    return item


@router.get("/{user_id}/orders")
async def get_profile_orders_route(user_id: int):
    items = await list_user_orders(user_id)
    return {
        "items": items,
        "count": len(items),
    }
