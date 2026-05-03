from pydantic import BaseModel, Field


class ParkingCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str | None = Field(default=None, max_length=100)
    description: str | None = None

    company_id: int | None = None

    source_type: str = Field(default="rtsp")
    source_url: str | None = None
    camera_name: str | None = None


class ParkingUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    slug: str | None = Field(default=None, max_length=100)
    description: str | None = None
    is_active: bool | None = None


class ParkingResponse(BaseModel):
    id: str
    db_id: int
    company_id: int
    name: str
    slug: str
    description: str | None = None
    is_active: bool

    layout_file_path: str | None = None
    map_file_path: str | None = None
    occupancy_file_path: str | None = None
    screenshot_file_path: str | None = None
    debug_frame_path: str | None = None

    spots_count: int = 0
    zones_count: int = 0
    summary: dict = {}

    class Config:
        from_attributes = True


class ParkingLayoutSave(BaseModel):
    layout: dict


class ParkingMapSave(BaseModel):
    map: dict