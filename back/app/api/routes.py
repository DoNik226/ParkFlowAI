from back.app.api.auth_routes import router as auth_router
from back.app.api.user_routes import router as user_router

__routes__ = [
    auth_router,
    user_router,
]
