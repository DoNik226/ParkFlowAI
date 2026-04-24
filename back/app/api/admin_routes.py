from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from back.app.api.deps import get_event_service
from back.app.api.stub_utils import not_implemented_response
from back.app.schemas.events import EventLogEntryResponse, EventLogListResponse
from back.app.schemas.stubs import (
    CalibrationRequest,
    CalibrationResponse,
    EditorCreateZoneRequest,
    EditorExportJsonResponse,
    EditorSaveRequest,
    EditorSaveResponse,
    EditorToggleSpotRequest,
    EditorUpdateSpotRequest,
    EditorZonesResponse,
    MessageResponse,
)
from back.app.services.event_service import EventService

router = APIRouter(tags=["admin"])


@router.get("/editor/parking/{parking_id}/zones", response_model=EditorZonesResponse)
async def get_editor_zones(parking_id: int):
    return not_implemented_response(
        "GET",
        f"/editor/parking/{parking_id}/zones",
        "Get parking editor zones and spots",
    )


@router.post("/editor/parking/{parking_id}/zones", response_model=MessageResponse)
async def create_editor_zone(parking_id: int, data: EditorCreateZoneRequest):
    return not_implemented_response(
        "POST",
        f"/editor/parking/{parking_id}/zones",
        "Create a parking editor zone",
    )


@router.put("/editor/spots/{spot_id}", response_model=MessageResponse)
async def update_editor_spot(spot_id: int, data: EditorUpdateSpotRequest):
    return not_implemented_response(
        "PUT",
        f"/editor/spots/{spot_id}",
        "Update parking spot polygon vertices",
    )


@router.delete("/editor/spots/{spot_id}", response_model=MessageResponse)
async def delete_editor_spot(spot_id: int):
    return not_implemented_response(
        "DELETE",
        f"/editor/spots/{spot_id}",
        "Delete a parking spot from the editor",
    )


@router.put("/editor/spots/{spot_id}/toggle", response_model=MessageResponse)
async def toggle_editor_spot(spot_id: int, data: EditorToggleSpotRequest):
    return not_implemented_response(
        "PUT",
        f"/editor/spots/{spot_id}/toggle",
        "Enable or disable a parking spot in the editor",
    )


@router.post("/editor/parking/{parking_id}/calibrate", response_model=CalibrationResponse)
async def calibrate_editor(parking_id: int, data: CalibrationRequest):
    return not_implemented_response(
        "POST",
        f"/editor/parking/{parking_id}/calibrate",
        "Calibrate parking editor scale",
    )


@router.post("/editor/parking/{parking_id}/export/json", response_model=EditorExportJsonResponse)
async def export_editor_json(parking_id: int):
    return not_implemented_response(
        "POST",
        f"/editor/parking/{parking_id}/export/json",
        "Export parking editor configuration as JSON",
    )


@router.get("/editor/parking/{parking_id}/export/png")
async def export_editor_png(parking_id: int, overlay: bool = True):
    return not_implemented_response(
        "GET",
        f"/editor/parking/{parking_id}/export/png",
        "Export parking editor overlay as PNG",
    )


@router.post("/editor/parking/{parking_id}/save", response_model=EditorSaveResponse)
async def save_editor_config(parking_id: int, data: EditorSaveRequest):
    return not_implemented_response(
        "POST",
        f"/editor/parking/{parking_id}/save",
        "Save parking editor configuration",
    )


def _build_entity_filters(object_type: str | None) -> list[str] | None:
    if object_type is None:
        return None
    if object_type == "users":
        return ["user", "admin"]
    return [object_type]


@router.get("/logs", response_model=EventLogListResponse)
async def list_logs(
    event_service: Annotated[EventService, Depends(get_event_service)],
    object_type: str | None = Query(default=None),
    parking_id: int | None = None,
    description: str | None = None,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    page: int = 1,
    limit: int = 50,
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
    event_service: Annotated[EventService, Depends(get_event_service)],
    parking_id: int | None = None,
    description: str | None = None,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    page: int = 1,
    limit: int = 50,
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
    event_service: Annotated[EventService, Depends(get_event_service)],
    description: str | None = None,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    page: int = 1,
    limit: int = 50,
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
    event_service: Annotated[EventService, Depends(get_event_service)],
    parking_id: int | None = None,
    description: str | None = None,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    page: int = 1,
    limit: int = 50,
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
