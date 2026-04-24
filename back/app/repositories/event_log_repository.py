from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from back.app.models.event_log import EventLog
from back.app.repositories.base_repository import BaseRepository


class EventLogRepository(BaseRepository[EventLog]):
    def __init__(self, db: Session):
        super().__init__(db, EventLog)

    def list_events(
        self,
        *,
        entity_types: Sequence[str] | None = None,
        parking_id: int | None = None,
        search: str | None = None,
        from_timestamp: datetime | None = None,
        to_timestamp: datetime | None = None,
        page: int = 1,
        limit: int = 50,
    ) -> tuple[int, list[EventLog]]:
        query = self.db.query(EventLog)

        if entity_types:
            query = query.filter(EventLog.entity_type.in_(entity_types))

        if parking_id is not None:
            query = query.filter(EventLog.parking_id == parking_id)

        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    EventLog.description.ilike(pattern),
                    EventLog.event_type.ilike(pattern),
                )
            )

        if from_timestamp is not None:
            query = query.filter(EventLog.timestamp >= from_timestamp)

        if to_timestamp is not None:
            query = query.filter(EventLog.timestamp <= to_timestamp)

        total = query.count()
        items = (
            query.order_by(EventLog.timestamp.desc(), EventLog.id.desc())
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )
        return total, items
