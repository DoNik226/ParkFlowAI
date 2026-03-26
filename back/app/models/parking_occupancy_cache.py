from sqlalchemy import Column, BigInteger, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from back.app.database import Base


class ParkingOccupancyCache(Base):
    __tablename__ = "parking_occupancy_cache"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    parking_id = Column(BigInteger, ForeignKey("parkings.id", ondelete="CASCADE"), unique=True)
    total_spots = Column(Integer, nullable=False, default=0)
    free_spots = Column(Integer, nullable=False, default=0)
    occupancy_percentage = Column(Float, nullable=False, default=0.0)
    last_calculated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    parking = relationship("Parking", backref="occupancy_cache")

    def __repr__(self):
        return f"<ParkingOccupancyCache(parking_id={self.parking_id}, free_spots={self.free_spots})>"