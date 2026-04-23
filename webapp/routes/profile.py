from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from webapp.auth import get_current_user
from webapp.services.profile_service import get_profile_summary, list_user_orders

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/me/summary")
async def get_profile_summary_route(user: dict = Depends(get_current_user)):
    user_id = user["id"]
    item = await get_profile_summary(user_id)
    if not item:
        raise HTTPException(status_code=404, detail="User not found")
    return item


@router.get("/me/orders")
async def get_profile_orders_route(user: dict = Depends(get_current_user)):
    user_id = user["id"]
    items = await list_user_orders(user_id)
    return {
        "items": items,
        "count": len(items),
    }

