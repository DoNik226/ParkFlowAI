from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from back.app.api.deps import get_event_service, require_admin
from back.app.models.user import User
from back.app.schemas.events import EventLogEntryResponse, EventLogListResponse
from back.app.services.event_service import EventService

router = APIRouter(tags=["admin"])


def _build_entity_filters(object_type: str | None) -> list[str] | None:
    if object_type is None:
        return None
    if object_type == "users":
        return ["user", "admin"]
    return [object_type]


@router.get("/logs", response_model=EventLogListResponse)
async def list_logs(
    _: Annotated[User, Depends(require_admin)],
    event_service: Annotated[EventService, Depends(get_event_service)],
    object_type: str | None = Query(default=None),
    parking_id: int | None = None,
    description: str | None = None,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
):
    return event_service.list_events(
        entity_types=_build_entity_filters(object_type),
        parking_id=parking_id,
        search=description,
        from_timestamp=from_,
        to_timestamp=to,
        page=page,
        limit=limit,
    )


@router.get("/logs/cameras", response_model=list[EventLogEntryResponse])
async def list_camera_logs(
    _: Annotated[User, Depends(require_admin)],
    event_service: Annotated[EventService, Depends(get_event_service)],
    parking_id: int | None = None,
    description: str | None = None,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
):
    result = event_service.list_events(
        entity_types=["camera"],
        parking_id=parking_id,
        search=description,
        from_timestamp=from_,
        to_timestamp=to,
        page=page,
        limit=limit,
    )
    return result["logs"]


@router.get("/logs/users", response_model=list[EventLogEntryResponse])
async def list_user_logs(
    _: Annotated[User, Depends(require_admin)],
    event_service: Annotated[EventService, Depends(get_event_service)],
    description: str | None = None,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
):
    result = event_service.list_events(
        entity_types=["user", "admin"],
        search=description,
        from_timestamp=from_,
        to_timestamp=to,
        page=page,
        limit=limit,
    )
    return result["logs"]


@router.get("/logs/parkings", response_model=list[EventLogEntryResponse])
async def list_parking_logs(
    _: Annotated[User, Depends(require_admin)],
    event_service: Annotated[EventService, Depends(get_event_service)],
    parking_id: int | None = None,
    description: str | None = None,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
):
    result = event_service.list_events(
        parking_id=parking_id,
        search=description,
        from_timestamp=from_,
        to_timestamp=to,
        page=page,
        limit=limit,
    )
    return [entry for entry in result["logs"] if entry["parking_id"] is not None]
