from sqlalchemy import Column, BigInteger, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from back.app.database import Base


class RoadEdge(Base):
    __tablename__ = "road_edges"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    source = Column(BigInteger, ForeignKey("road_vertices.id", ondelete="CASCADE"))
    destination = Column(BigInteger, ForeignKey("road_vertices.id", ondelete="CASCADE"))
    length_meters = Column(Float, nullable=False)
    one_way = Column(Boolean, nullable=False, default=False)
    is_bidirectional = Column(Boolean, nullable=False, default=True)

    # Relationships
    source_vertex = relationship("RoadVertex", foreign_keys=[source], backref="outgoing_edges")
    destination_vertex = relationship("RoadVertex", foreign_keys=[destination], backref="incoming_edges")

    def __repr__(self):
        return f"<RoadEdge(id={self.id}, source={self.source}, destination={self.destination})>"