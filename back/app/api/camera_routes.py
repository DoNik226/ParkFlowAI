from fastapi import APIRouter

from back.app.api.stub_utils import not_implemented_response
from back.app.schemas.stubs import CameraResponse, CameraUpsertRequest, MessageResponse

router = APIRouter(prefix="/cameras", tags=["cameras"])


@router.get("", response_model=list[CameraResponse])
async def list_cameras(parking_id: int | None = None):
    return not_implemented_response("GET", "/cameras", "List cameras, optionally filtered by parking_id")


@router.get("/{camera_id}", response_model=CameraResponse)
async def get_camera(camera_id: int):
    return not_implemented_response("GET", f"/cameras/{camera_id}", "Get camera details")


@router.post("", response_model=MessageResponse)
async def create_camera(data: CameraUpsertRequest):
    return not_implemented_response("POST", "/cameras", "Create a camera")


@router.put("/{camera_id}", response_model=MessageResponse)
async def update_camera(camera_id: int, data: CameraUpsertRequest):
    return not_implemented_response("PUT", f"/cameras/{camera_id}", "Update a camera")


@router.delete("/{camera_id}", response_model=MessageResponse)
async def delete_camera(camera_id: int):
    return not_implemented_response("DELETE", f"/cameras/{camera_id}", "Delete a camera")


@router.post("/{camera_id}/reconnect", response_model=MessageResponse)
async def reconnect_camera(camera_id: int):
    return not_implemented_response(
        "POST",
        f"/cameras/{camera_id}/reconnect",
        "Trigger camera reconnection",
    )


@router.get("/{camera_id}/stream")
async def get_camera_stream(camera_id: int):
    return not_implemented_response(
        "GET",
        f"/cameras/{camera_id}/stream",
        "Return an MJPEG or HLS camera stream",
    )


@router.get("/{camera_id}/snapshot")
async def get_camera_snapshot(camera_id: int):
    return not_implemented_response(
        "GET",
        f"/cameras/{camera_id}/snapshot",
        "Return the latest camera snapshot",
    )
