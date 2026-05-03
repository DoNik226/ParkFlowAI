from sqlalchemy import Column, BigInteger, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from back.app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    users = relationship("User", back_populates="company")
    parkings = relationship("Parking", back_populates="company")

    def __repr__(self):
        return f"<Company(id={self.id}, slug={self.slug})>"