from sqlalchemy.orm import relationship

from back.app.models.company import Company
from back.app.models.event_log import EventLog
from back.app.models.login_attempt import LoginAttempt
from back.app.models.user import User
from back.app.models.parking import Parking
from back.app.models.camera import Camera
from back.app.models.road_vertex import RoadVertex
from back.app.models.road_edge import RoadEdge
from back.app.models.parking_spot import ParkingSpot


def configure_relationships():
    """Настройка отношений после импорта всех моделей."""

    if not hasattr(RoadVertex, "parking"):
        RoadVertex.parking = relationship("Parking", back_populates="vertices")

    if not hasattr(Parking, "vertices"):
        Parking.vertices = relationship("RoadVertex", back_populates="parking")


configure_relationships()


__all__ = [
    "Company",
    "EventLog",
    "LoginAttempt",
    "User",
    "Parking",
    "Camera",
    "RoadVertex",
    "RoadEdge",
    "ParkingSpot",
]
