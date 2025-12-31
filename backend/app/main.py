from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.routers import campaigns_router, script_config_router
from app.routers.settings import router as settings_router
from app.routers.sync import router as sync_router
from app.routers.shopify import router as shopify_router
from app.routers.shopify_proxy import router as shopify_proxy_router
from app.routers.shipping import router as shipping_router
from app.routers.products import router as products_router
from app.routers.meta import router as meta_router
from app.background_tasks import shopify_sync_task, meta_sync_task, shipping_calculation_task


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup: Start background tasks
    shopify_sync_task.interval_hours = settings.shopify_sync_interval_hours
    shopify_sync_task.start()
    meta_sync_task.start()
    shipping_calculation_task.start()
    yield
    # Shutdown: Stop background tasks
    await shopify_sync_task.stop()
    await meta_sync_task.stop()
    await shipping_calculation_task.stop()


app = FastAPI(
    title="Marketing Campaign Tracker API",
    description="API for monitoring marketing campaigns across multiple ad platforms",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public routes (no auth required)
app.include_router(sync_router)
app.include_router(shopify_router)
app.include_router(shopify_proxy_router)
app.include_router(script_config_router)  # Public so Google Ads script can fetch config

# Protected routes (HTTP Basic Auth required)
app.include_router(campaigns_router)
app.include_router(settings_router)
app.include_router(products_router)
app.include_router(meta_router)
app.include_router(shipping_router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "message": "Marketing Campaign Tracker API",
        "version": "0.1.0"
    }


@app.get("/health")
async def health():
    """Health check endpoint for monitoring."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
