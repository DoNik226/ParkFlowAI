from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EventLogEntryResponse(BaseModel):
    id: int
    timestamp: datetime
    event_type: str
    severity: str
    entity_type: str
    entity_id: int | None = None
    entity_name: str | None = None
    actor_user_id: int | None = None
    actor_username: str | None = None
    parking_id: int | None = None
    parking_name: str | None = None
    description: str
    details: dict[str, Any] = Field(default_factory=dict)


class EventLogListResponse(BaseModel):
    total: int
    page: int
    limit: int
    logs: list[EventLogEntryResponse]
