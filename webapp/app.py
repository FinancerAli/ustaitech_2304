from fastapi import FastAPI

from webapp.routes.catalog import router as catalog_router
from webapp.routes.profile import router as profile_router

app = FastAPI(
    title="UstAiTech Mini App API",
    version="0.1.0",
)

app.include_router(catalog_router, prefix='/api')
app.include_router(profile_router, prefix='/api')


@app.get("/health")
async def health():
    return {
        "ok": True,
        "service": "ust_ai_tech_miniapp_api",
    }
