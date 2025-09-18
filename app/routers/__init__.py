# Routers package
from . import auth_router
from . import analysis_router
from . import appointments_router
from . import doctors_router
from . import devices_router
from . import health_analytics_router
from . import notifications_router
from . import settings_router

__all__ = [
    "auth_router",
    "analysis_router",
    "appointments_router", 
    "doctors_router",
    "devices_router",
    "health_analytics_router",
    "notifications_router",
    "settings_router"
]