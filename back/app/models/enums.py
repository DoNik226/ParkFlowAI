from enum import Enum

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"

class CameraStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"

class SpotStatus(str, Enum):
    FREE = "free"
    OCCUPIED = "occupied"


class EventEntityType(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ADMIN = "admin"
    CAMERA = "camera"


class EventSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class EventType(str, Enum):
    APP_STARTED = "app_started"
    APP_STOPPED = "app_stopped"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    ADMIN_ACTION = "admin_action"
    CAMERA_CONNECTED = "camera_connected"
    CAMERA_CONNECTION_LOST = "camera_connection_lost"
    CAMERA_CONNECTION_RESTORED = "camera_connection_restored"
    DETECTION_ERROR = "detection_error"
    VIDEO_PROCESSING_ERROR = "video_processing_error"
