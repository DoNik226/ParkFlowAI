from sqlalchemy.orm import relationship

from back.app.models.login_attempt import LoginAttempt
from back.app.models.user import User
from back.app.models.parking import Parking
from back.app.models.road_vertex import RoadVertex
from back.app.models.road_edge import RoadEdge
from back.app.models.parking_spot import ParkingSpot


# Настраиваем отношения ПОСЛЕ импорта всех моделей
def configure_relationships():
    """Настройка отношений после импорта всех моделей"""
    from back.app.models.road_vertex import RoadVertex
    from back.app.models.parking import Parking

    # Добавляем relationship динамически
    if not hasattr(RoadVertex, 'parking'):
        RoadVertex.parking = relationship("Parking", back_populates="vertices")
    if not hasattr(Parking, 'vertices'):
        Parking.vertices = relationship("RoadVertex", back_populates="parking")



# Вызываем настройку после импорта
configure_relationships()

__all__ = ["LoginAttempt",
    "User", 'Parking', 'RoadVertex', 'RoadEdge', 'ParkingSpot']