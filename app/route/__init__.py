from .health import router as health_router
from .processing import router as processing_router

__all__ = [
    "health_router",
    "processing_router"
]
