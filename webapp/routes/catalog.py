from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from webapp.services.catalog_service import (
    get_service_detail,
    list_active_promotions,
    list_services,
)

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/services")
async def get_catalog_services(
    only_active: bool = True,
    category_id: int | None = None,
    query: str | None = None,
    limit: int | None = Query(default=None, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    items = await list_services(
        only_active=only_active,
        category_id=category_id,
        query=query,
        limit=limit,
        offset=offset,
    )
    return {
        "items": items,
        "count": len(items),
    }


@router.get("/services/{service_id}")
async def get_catalog_service_detail(service_id: int):
    item = await get_service_detail(service_id)
    if not item:
        raise HTTPException(status_code=404, detail="Service not found")
    return item


@router.get("/promotions/active")
async def get_catalog_active_promotions():
    items = await list_active_promotions()
    return {
        "items": items,
        "count": len(items),
    }
