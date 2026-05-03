from back.app.api.admin_routes import router as admin_router
from back.app.api.auth_routes import router as auth_router
from back.app.api.user_routes import router as user_router
from back.app.api.map_routes import router as map_router

__routes__ = [
    admin_router,
    auth_router,
    user_router,
    map_router
]
