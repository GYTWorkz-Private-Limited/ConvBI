"""
Routes package for Text2SQL API
"""

from .chat import router as chat_router
from .index import router as index_router
from .health import router as health_router

__all__ = ["chat_router", "index_router", "health_router"]

