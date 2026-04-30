from sqlalchemy import Column, BigInteger, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from back.app.database import Base
from back.app.models.enums import CameraStatus, CameraSourceType


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    parking_id = Column(
        BigInteger,
        ForeignKey("parkings.id", ondelete="CASCADE"),
        nullable=False,
    )

    name = Column(String(100), nullable=False)

    source_type = Column(String(20), nullable=False, default=CameraSourceType.RTSP.value)
    source_url = Column(String(1000), nullable=True)
    test_video_path = Column(String(500), nullable=True)

    status = Column(String(20), nullable=False, default=CameraStatus.OFFLINE.value)
    is_active = Column(Boolean, nullable=False, default=True)

    last_snapshot_path = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    parking = relationship("Parking", back_populates="cameras")

    def __repr__(self):
        return f"<Camera(id={self.id}, name={self.name}, source_type={self.source_type})>"