"""
API Routes Package for CCTNS Copilot Engine
"""
from .voice import router as voice_router
from .query import router as query_router

# Import other routers when they're available
try:
    from .reports import router as reports_router
except ImportError:
    reports_router = None

try:
    from .chat import router as chat_router
except ImportError:
    chat_router = None

__all__ = ['voice_router', 'query_router', 'reports_router', 'chat_router']