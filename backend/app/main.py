from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import campaigns_router
from app.routers.settings import router as settings_router
from app.routers.sync import router as sync_router

app = FastAPI(
    title="Marketing Campaign Tracker API",
    description="API for monitoring marketing campaigns across multiple ad platforms",
    version="0.1.0",
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

# Protected routes (HTTP Basic Auth required)
app.include_router(campaigns_router)
app.include_router(settings_router)


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
