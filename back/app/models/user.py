from sqlalchemy import Column, BigInteger, String, Boolean, Integer, DateTime
from sqlalchemy.sql import func
from back.app.database import Base
from back.app.models.enums import UserRole


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default=UserRole.USER.value)
    full_name = Column(String(255))
    is_active = Column(Boolean, nullable=False, default=True)
    failed_attempts = Column(Integer, nullable=False, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"
