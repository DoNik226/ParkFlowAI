from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from back.app.database import Base
from back.app.models.enums import EventEntityType, EventSeverity


class EventLog(Base):
    __tablename__ = "event_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    event_type = Column(String(64), nullable=False)
    severity = Column(String(20), nullable=False, default=EventSeverity.INFO.value)
    entity_type = Column(String(20), nullable=False, default=EventEntityType.SYSTEM.value)
    entity_id = Column(BigInteger, nullable=True)
    actor_user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    parking_id = Column(BigInteger, ForeignKey("parkings.id", ondelete="SET NULL"), nullable=True)
    description = Column(Text, nullable=False)
    details = Column(JSON, nullable=False, default=dict)

    actor_user = relationship("User", foreign_keys=[actor_user_id], lazy="joined")
    parking = relationship("Parking", foreign_keys=[parking_id], lazy="joined")

    def __repr__(self):
        return (
            f"<EventLog(id={self.id}, event_type={self.event_type}, "
            f"entity_type={self.entity_type}, entity_id={self.entity_id})>"
        )
