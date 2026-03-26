from sqlalchemy import Column, BigInteger, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from back.app.database import Base
from back.app.models.enums import CameraStatus


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    rtsp_url = Column(String(500), nullable=False)
    parking_id = Column(BigInteger, ForeignKey("parkings.id", ondelete="CASCADE"))
    status = Column(String(20), nullable=False, default=CameraStatus.OFFLINE.value)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    parking = relationship("Parking", backref="cameras")

    def __repr__(self):
        return f"<Camera(id={self.id}, name={self.name}, status={self.status})>"