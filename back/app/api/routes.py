from back.app.api.auth_routes import router as auth_router
from back.app.api.user_routes import router as user_router
from back.app.api.map_routes import router as map_router
from back.app.api.detection_routes import router as detection_router

__routes__ = [
    auth_router,
    user_router,
    map_router,
    detection_router # памагити, я устал (
]
