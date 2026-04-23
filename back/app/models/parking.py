from sqlalchemy import Column, BigInteger, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
from back.app.database import Base


class Parking(Base):
    __tablename__ = "parkings"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    config_file_path = Column(String(255))
    is_active = Column(Boolean, nullable=False, default=True)

    def __repr__(self):
        return f"<Parking(id={self.id}, name={self.name})>"