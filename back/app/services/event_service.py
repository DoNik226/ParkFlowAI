from collections.abc import Sequence
from datetime import datetime
from typing import Any

from back.app.models.enums import EventEntityType, EventSeverity
from back.app.repositories.camera_repository import CameraRepository
from back.app.repositories.event_log_repository import EventLogRepository
from back.app.repositories.parking_repository import ParkingRepository
from back.app.repositories.user_repository import UserRepository


class EventService:
    def __init__(
        self,
        event_log_repository: EventLogRepository,
        user_repository: UserRepository,
        camera_repository: CameraRepository,
        parking_repository: ParkingRepository,
    ):
        self.event_log_repository = event_log_repository
        self.user_repository = user_repository
        self.camera_repository = camera_repository
        self.parking_repository = parking_repository

    def create_event(
        self,
        *,
        event_type: str,
        description: str,
        severity: str = EventSeverity.INFO.value,
        entity_type: str = EventEntityType.SYSTEM.value,
        entity_id: int | None = None,
        actor_user_id: int | None = None,
        parking_id: int | None = None,
        details: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ):
        payload = {
            "event_type": event_type,
            "description": description,
            "severity": severity,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "actor_user_id": actor_user_id,
            "parking_id": parking_id,
            "details": details or {},
        }
        if timestamp is not None:
            payload["timestamp"] = timestamp
        return self.event_log_repository.create(**payload)

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
    ) -> dict[str, Any]:
        total, items = self.event_log_repository.list_events(
            entity_types=entity_types,
            parking_id=parking_id,
            search=search,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            page=page,
            limit=limit,
        )
        return {
            "total": total,
            "page": page,
            "limit": limit,
            "logs": self._serialize_events(items),
        }

    def _serialize_events(self, items) -> list[dict[str, Any]]:
        actor_ids = {int(item.actor_user_id) for item in items if item.actor_user_id is not None}
        parking_ids = {int(item.parking_id) for item in items if item.parking_id is not None}
        camera_ids = {
            int(item.entity_id)
            for item in items
            if item.entity_type == EventEntityType.CAMERA.value and item.entity_id is not None
        }
        subject_user_ids = {
            int(item.entity_id)
            for item in items
            if item.entity_type in {EventEntityType.USER.value, EventEntityType.ADMIN.value}
            and item.entity_id is not None
        }

        users = {
            int(user.id): user
            for user in self.user_repository.list_by_ids(list(actor_ids | subject_user_ids))
        }
        parkings = {
            int(parking.id): parking
            for parking in self.parking_repository.list_by_ids(list(parking_ids))
        }
        cameras = {
            int(camera.id): camera
            for camera in self.camera_repository.list_by_ids(list(camera_ids))
        }

        result = []
        for item in items:
            entity_name = None
            if item.entity_type == EventEntityType.CAMERA.value and item.entity_id is not None:
                camera = cameras.get(int(item.entity_id))
                entity_name = camera.name if camera else None
            elif item.entity_type in {EventEntityType.USER.value, EventEntityType.ADMIN.value}:
                if item.entity_id is not None:
                    user = users.get(int(item.entity_id))
                    if user:
                        entity_name = user.full_name or user.username

            actor = users.get(int(item.actor_user_id)) if item.actor_user_id is not None else None
            parking = parkings.get(int(item.parking_id)) if item.parking_id is not None else None

            result.append(
                {
                    "id": item.id,
                    "timestamp": item.timestamp,
                    "event_type": item.event_type,
                    "severity": item.severity,
                    "entity_type": item.entity_type,
                    "entity_id": item.entity_id,
                    "entity_name": entity_name,
                    "actor_user_id": item.actor_user_id,
                    "actor_username": actor.username if actor else None,
                    "parking_id": item.parking_id,
                    "parking_name": parking.name if parking else None,
                    "description": item.description,
                    "details": item.details or {},
                }
            )

        return result
