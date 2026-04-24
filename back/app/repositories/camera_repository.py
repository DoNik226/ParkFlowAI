from typing import Optional, List
from sqlalchemy.orm import Session
from back.app.models.camera import Camera
from back.app.repositories.base_repository import BaseRepository
from back.app.models.enums import CameraStatus


class CameraRepository(BaseRepository[Camera]):
    def __init__(self, db: Session):
        super().__init__(db, Camera)

    def get_by_parking(self, parking_id: int, skip: int = 0, limit: int = 100) -> List[Camera]:
        return self.db.query(Camera).filter(Camera.parking_id == parking_id).offset(skip).limit(limit).all()

    def get_by_status(self, status: CameraStatus, skip: int = 0, limit: int = 100) -> List[Camera]:
        return self.db.query(Camera).filter(Camera.status == status.value).offset(skip).limit(limit).all()

    def update_status(self, camera_id: int, status: CameraStatus) -> Optional[Camera]:
        return self.update(camera_id, status=status.value)

    def list_by_ids(self, camera_ids: list[int]) -> List[Camera]:
        if not camera_ids:
            return []
        return self.db.query(Camera).filter(Camera.id.in_(camera_ids)).all()
