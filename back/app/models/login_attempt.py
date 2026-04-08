from sqlalchemy import BigInteger, Boolean, Column, DateTime, String
from sqlalchemy.sql import func

from back.app.database import Base


class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    ip_address = Column(String(45), nullable=False)
    login = Column(String(255), nullable=False)
    was_successful = Column(Boolean, nullable=False, default=False)
    attempted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
