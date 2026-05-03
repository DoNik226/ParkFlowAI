import logging
from typing import Any

from back.app.models.enums import EventEntityType, EventSeverity, EventType
from back.app.services.event_service import EventService


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("parkflow")
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


class EventLogger:
    def __init__(self, event_service: EventService):
        self.event_service = event_service
        self.logger = configure_logging()

    def log(
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
    ) -> None:
        try:
            self.event_service.create_event(
                event_type=event_type,
                description=description,
                severity=severity,
                entity_type=entity_type,
                entity_id=entity_id,
                actor_user_id=actor_user_id,
                parking_id=parking_id,
                details=details,
            )
        except Exception:
            self.logger.exception("Failed to persist event log entry")

    def log_system_started(self) -> None:
        self.log(
            event_type=EventType.APP_STARTED.value,
            description="Приложение запущено",
        )

    def log_system_stopped(self) -> None:
        self.log(
            event_type=EventType.APP_STOPPED.value,
            description="Приложение остановлено",
        )


class AuditLogger(EventLogger):
    def log_user_login(self, user_id: int, *, entity_type: str) -> None:
        self.log(
            event_type=EventType.USER_LOGIN.value,
            description="Пользователь вошел в систему",
            entity_type=entity_type,
            entity_id=user_id,
            actor_user_id=user_id,
        )

    def log_user_logout(self, user_id: int, *, entity_type: str) -> None:
        self.log(
            event_type=EventType.USER_LOGOUT.value,
            description="Пользователь вышел из системы",
            entity_type=entity_type,
            entity_id=user_id,
            actor_user_id=user_id,
        )

    def log_admin_action(
        self,
        admin_user_id: int,
        description: str,
        *,
        entity_type: str = EventEntityType.ADMIN.value,
        entity_id: int | None = None,
        parking_id: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.log(
            event_type=EventType.ADMIN_ACTION.value,
            description=description,
            entity_type=entity_type,
            entity_id=entity_id if entity_id is not None else admin_user_id,
            actor_user_id=admin_user_id,
            parking_id=parking_id,
            details=details,
        )
