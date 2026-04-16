from sqlalchemy import Column, BigInteger, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from back.app.database import Base


class RoadVertex(Base):
    __tablename__ = "road_vertices"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    is_spot = Column(Boolean, nullable=False, default=False)
    is_entrance = Column(Boolean, nullable=False, default=False)
    parking_id = Column(BigInteger, ForeignKey("parkings.id", ondelete="CASCADE"))

    def __repr__(self):
        return f"<RoadVertex(id={self.id}, is_spot={self.is_spot}, is_entrance={self.is_entrance})>"