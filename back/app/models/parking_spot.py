from sqlalchemy import Column, BigInteger, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from back.app.database import Base
from back.app.models.enums import SpotStatus


class ParkingSpot(Base):
    __tablename__ = "parking_spots"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    parking_id = Column(BigInteger, ForeignKey("parkings.id", ondelete="CASCADE"))
    status = Column(String(20), nullable=False, default=SpotStatus.FREE.value)
    spot_number = Column(String(20), nullable=False)
    road_vertex_id = Column(BigInteger, ForeignKey("road_vertices.id"))

    # Relationships
    parking = relationship("Parking", backref="parking_spots")
    road_vertex = relationship("RoadVertex", backref="parking_spot")

    def __repr__(self):
        return f"<ParkingSpot(id={self.id}, spot_number={self.spot_number}, status={self.status})>"