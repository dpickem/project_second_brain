"""API Routers package."""

from app.routers import health as health_router
from app.routers import capture as capture_router
from app.routers import ingestion as ingestion_router
from app.routers import processing as processing_router
from app.routers import vault as vault_router
from app.routers import knowledge as knowledge_router
from app.routers import practice as practice_router
from app.routers import review as review_router
from app.routers import analytics as analytics_router

__all__ = [
    "health_router",
    "capture_router",
    "ingestion_router",
    "processing_router",
    "vault_router",
    "knowledge_router",
    "practice_router",
    "review_router",
    "analytics_router",
]
