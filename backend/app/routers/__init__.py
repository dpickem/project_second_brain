"""API Routers package."""

from app.routers import health as health_router
from app.routers import capture as capture_router
from app.routers import ingestion as ingestion_router
from app.routers import processing as processing_router
from app.routers import vault as vault_router
from app.routers import knowledge as knowledge_router

__all__ = [
    "health_router",
    "capture_router",
    "ingestion_router",
    "processing_router",
    "vault_router",
    "knowledge_router",
]
