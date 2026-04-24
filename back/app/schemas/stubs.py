from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    message: str


class ForgotPasswordRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)


class ParkingUpsertRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    is_active: bool = True


class ParkingListItem(BaseModel):
    id: int
    name: str
    description: str | None = None
    is_active: bool
    total_spots: int
    free_spots: int
    occupancy_percentage: float


class ParkingDetailResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    config_file_path: str | None = None
    is_active: bool


class ParkingOccupancyResponse(BaseModel):
    parking_id: int
    total_spots: int
    free_spots: int
    occupancy_percentage: float
    last_calculated: datetime


class CameraUpsertRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    rtsp_url: str = Field(min_length=1, max_length=500)
    parking_id: int = Field(gt=0)


class CameraResponse(BaseModel):
    id: int
    name: str
    rtsp_url: str
    parking_id: int
    status: str


class ParkingSpotResponse(BaseModel):
    id: int
    spot_number: str
    status: str
    road_vertex_id: int | None = None


class ParkingSpotStatusUpdateRequest(BaseModel):
    status: str


class FreeSpotResponse(BaseModel):
    spot_id: int
    spot_number: str
    distance: float


class EntranceResponse(BaseModel):
    id: int
    name: str
    road_vertex_id: int


class NearestParkingResponse(BaseModel):
    parking_id: int
    name: str
    distance: float
    free_spots: int


class EditorZoneSummary(BaseModel):
    id: int
    name: str
    spots_count: int
    rows: int
    spots_per_row: int


class EditorSpotPolygon(BaseModel):
    id: int
    vertices: list[dict[str, float]]
    enabled: bool = True


class EditorZonesResponse(BaseModel):
    zones: list[EditorZoneSummary]
    spots: list[EditorSpotPolygon]


class EditorCreateZoneRequest(BaseModel):
    rows: int = Field(gt=0)
    spots_per_row: int = Field(gt=0)
    spot_width: float = Field(gt=0)


class EditorUpdateSpotRequest(BaseModel):
    vertices: list[dict[str, float]]


class EditorToggleSpotRequest(BaseModel):
    enabled: bool


class CalibrationRequest(BaseModel):
    pixel_distance: float = Field(gt=0)
    real_distance: float = Field(gt=0)


class CalibrationResponse(BaseModel):
    scale: float
    message: str


class EditorExportJsonResponse(BaseModel):
    config: dict[str, Any]


class EditorSaveRequest(BaseModel):
    config_file: dict[str, Any]


class EditorSaveResponse(BaseModel):
    message: str
    file_path: str


class LogEntryResponse(BaseModel):
    id: int
    timestamp: datetime
    type: str
    user_id: int | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class LogListResponse(BaseModel):
    total: int
    logs: list[LogEntryResponse]
