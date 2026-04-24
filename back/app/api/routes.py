from back.app.api.admin_routes import router as admin_router
from back.app.api.auth_routes import router as auth_router
from back.app.api.camera_routes import router as camera_router
from back.app.api.parking_routes import router as parking_router
from back.app.api.user_routes import router as user_router
from back.app.api.map_routes import router as map_router

__routes__ = [
    auth_router,
    user_router,
    map_router,
    parking_router,
    camera_router,
    admin_router,
]
