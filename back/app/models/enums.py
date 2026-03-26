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