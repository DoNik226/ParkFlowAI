from sqlalchemy import Column, BigInteger, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from back.app.database import Base


class Entrance(Base):
    __tablename__ = "entrances"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    parking_id = Column(BigInteger, ForeignKey("parkings.id", ondelete="CASCADE"))
    road_vertex_id = Column(BigInteger, ForeignKey("road_vertices.id"))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    parking = relationship("Parking", backref="entrances")
    road_vertex = relationship("RoadVertex", backref="entrance")

    def __repr__(self):
        return f"<Entrance(id={self.id}, name={self.name})>"