from pydantic import BaseModel, Field


class CameraCreate(BaseModel):
    parking_id: str
    name: str = Field(min_length=1, max_length=100)
    source_type: str = Field(default="rtsp")
    source_url: str | None = None


class CameraUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    source_type: str | None = None
    source_url: str | None = None
    is_active: bool | None = None


class CameraResponse(BaseModel):
    id: int
    parking_id: int
    name: str
    source_type: str
    source_url: str | None = None
    test_video_path: str | None = None
    status: str
    is_active: bool
    last_snapshot_path: str | None = None

    class Config:
        from_attributes = True