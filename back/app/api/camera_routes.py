from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from back.app.api.deps import get_current_active_user, require_admin, assert_same_company_or_super_admin
from back.app.database import get_db
from back.app.models.enums import CameraSourceType, CameraStatus
from back.app.models.user import User
from back.app.repositories.camera_repository import CameraRepository
from back.app.repositories.parking_repository import ParkingRepository
from back.app.schemas.cameras import CameraCreate, CameraUpdate, CameraResponse

router = APIRouter(prefix="/cameras", tags=["cameras"])


def resolve_camera(camera_id: int, db: Session, current_user: User):
    camera_repo = CameraRepository(db)
    parking_repo = ParkingRepository(db)

    camera = camera_repo.get_by_id(camera_id)

    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    parking = parking_repo.get_by_id(camera.parking_id)

    if not parking:
        raise HTTPException(status_code=404, detail="Parking not found")

    assert_same_company_or_super_admin(current_user, parking.company_id)

    return camera, parking


@router.get("", response_model=list[CameraResponse])
def list_cameras(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    parking_id: str | None = None,
):
    camera_repo = CameraRepository(db)
    parking_repo = ParkingRepository(db)

    if parking_id:
        parking = parking_repo.get_by_id_or_slug(parking_id)
        if not parking:
            raise HTTPException(status_code=404, detail="Parking not found")

        assert_same_company_or_super_admin(current_user, parking.company_id)
        return camera_repo.get_by_parking(parking.id)

    if current_user.role == "super_admin":
        return camera_repo.get_all(limit=1000)

    if current_user.company_id is None:
        return []

    parkings = parking_repo.list_for_company(current_user.company_id, limit=1000)
    parking_ids = [parking.id for parking in parkings]

    result = []
    for pid in parking_ids:
        result.extend(camera_repo.get_by_parking(pid))

    return result


@router.get("/{camera_id}", response_model=CameraResponse)
def get_camera(
    camera_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    camera, _parking = resolve_camera(camera_id, db, current_user)
    return camera


@router.post("", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
def create_camera(
    data: CameraCreate,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    camera_repo = CameraRepository(db)
    parking_repo = ParkingRepository(db)

    parking = parking_repo.get_by_id_or_slug(data.parking_id)

    if not parking:
        raise HTTPException(status_code=404, detail="Parking not found")

    assert_same_company_or_super_admin(current_user, parking.company_id)

    if data.source_type not in {
        CameraSourceType.RTSP.value,
        CameraSourceType.VIDEO.value,
        CameraSourceType.IMAGE.value,
    }:
        raise HTTPException(status_code=400, detail="Invalid source_type")

    return camera_repo.create(
        parking_id=parking.id,
        name=data.name,
        source_type=data.source_type,
        source_url=data.source_url,
        status=CameraStatus.OFFLINE.value,
        is_active=True,
    )


@router.put("/{camera_id}", response_model=CameraResponse)
def update_camera(
    camera_id: int,
    data: CameraUpdate,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    camera_repo = CameraRepository(db)
    camera, _parking = resolve_camera(camera_id, db, current_user)

    update_data = data.model_dump(exclude_unset=True)

    if "source_type" in update_data and update_data["source_type"] not in {
        CameraSourceType.RTSP.value,
        CameraSourceType.VIDEO.value,
        CameraSourceType.IMAGE.value,
    }:
        raise HTTPException(status_code=400, detail="Invalid source_type")

    return camera_repo.update(camera.id, **update_data)


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_camera(
    camera_id: int,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    camera_repo = CameraRepository(db)
    camera, _parking = resolve_camera(camera_id, db, current_user)
    camera_repo.delete(camera.id)


@router.post("/{camera_id}/reconnect")
def reconnect_camera(
    camera_id: int,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    camera, _parking = resolve_camera(camera_id, db, current_user)

    return {
        "camera_id": camera.id,
        "status": "ok",
        "message": "Команда переподключения принята",
        "camera": CameraResponse.model_validate(camera),
    }


@router.get("/{camera_id}/stream")
def get_camera_stream(
    camera_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    camera, _parking = resolve_camera(camera_id, db, current_user)

    raise HTTPException(
        status_code=501,
        detail={
            "message": "Проксирование видеопотока пока не реализовано",
            "camera_id": camera.id,
            "source_type": camera.source_type,
        },
    )


@router.get("/{camera_id}/snapshot")
def get_camera_snapshot(
    camera_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    camera, _parking = resolve_camera(camera_id, db, current_user)

    raise HTTPException(
        status_code=501,
        detail={
            "message": "Snapshot через camera endpoint пока не реализован. Используй /parkings/{parking_id}/snapshot",
            "camera_id": camera.id,
        },
    )