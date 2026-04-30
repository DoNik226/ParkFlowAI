from sqlalchemy import Column, BigInteger, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from back.app.database import Base


class Parking(Base):
    __tablename__ = "parkings"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    company_id = Column(
        BigInteger,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )

    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False)
    description = Column(Text)

    layout_file_path = Column(String(500), nullable=True)
    map_file_path = Column(String(500), nullable=True)
    occupancy_file_path = Column(String(500), nullable=True)
    screenshot_file_path = Column(String(500), nullable=True)
    debug_frame_path = Column(String(500), nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    company = relationship("Company", back_populates="parkings")
    cameras = relationship("Camera", back_populates="parking", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Parking(id={self.id}, name={self.name}, company_id={self.company_id})>"