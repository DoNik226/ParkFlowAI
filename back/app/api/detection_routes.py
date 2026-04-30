from pathlib import Path
import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from back.app.api.deps import get_current_active_user, require_admin, assert_same_company_or_super_admin
from back.app.database import get_db
from back.app.models.enums import CameraSourceType, UserRole
from back.app.models.user import User
from back.app.repositories.camera_repository import CameraRepository
from back.app.repositories.company_repository import CompanyRepository
from back.app.repositories.parking_repository import ParkingRepository

router = APIRouter(prefix="/parkings/{parking_id}/detector", tags=["detector"])

DATA_ROOT = Path("/app/data/companies")
DEFAULT_MODEL_PATH = "/app/models/best.pt"


def read_json(path: Path, default: Any = None):
    if not path.exists():
        return default

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = path.with_suffix(path.suffix + ".tmp")

    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    temp_path.replace(path)


def get_company_slug(db: Session, company_id: int) -> str:
    company = CompanyRepository(db).get_by_id(company_id)

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    return company.slug


def parking_storage_dir(db: Session, parking) -> Path:
    company_slug = get_company_slug(db, parking.company_id)
    return DATA_ROOT / company_slug / "parkings" / parking.slug


def resolve_parking(parking_id: str, db: Session, current_user: User):
    repo = ParkingRepository(db)

    if current_user.role == UserRole.SUPER_ADMIN.value:
        parking = repo.get_by_id_or_slug(parking_id)
    else:
        parking = repo.get_by_id_or_slug(parking_id, company_id=current_user.company_id)

    if not parking:
        raise HTTPException(status_code=404, detail="Parking not found")

    assert_same_company_or_super_admin(current_user, parking.company_id)

    return parking


def get_camera_or_404(db: Session, parking_id: int):
    camera = CameraRepository(db).get_first_by_parking(parking_id)

    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    return camera


def detector_control_path(db: Session, parking) -> Path:
    return parking_storage_dir(db, parking) / "detector_control.json"


def build_detector_config(db: Session, parking, active: bool) -> dict:
    camera = get_camera_or_404(db, parking.id)

    source_type = camera.source_type or CameraSourceType.RTSP.value

    if source_type == CameraSourceType.VIDEO.value:
        source = camera.test_video_path
    else:
        source = camera.source_url

    if not source:
        raise HTTPException(
            status_code=400,
            detail="Camera source is empty. Upload video or set RTSP URL first.",
        )

    if not parking.layout_file_path:
        raise HTTPException(status_code=400, detail="Layout path is empty")

    if not parking.occupancy_file_path:
        raise HTTPException(status_code=400, detail="Occupancy path is empty")

    return {
        "parking_id": parking.slug,
        "parking_db_id": parking.id,
        "company_id": parking.company_id,
        "active": active,
        "source_type": source_type,
        "source": source,
        "layout_path": parking.layout_file_path,
        "save_json": parking.occupancy_file_path,
        "save_frame": parking.debug_frame_path,
        "model": DEFAULT_MODEL_PATH,
        "interval_sec": 1.0,
        "loop_video": source_type == CameraSourceType.VIDEO.value,
        "is_live": source_type == CameraSourceType.RTSP.value,
        "conf": 0.10,
        "imgsz": 640,
    }


@router.get("/status")
def get_detector_status(
    parking_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    parking = resolve_parking(parking_id, db, current_user)
    camera = get_camera_or_404(db, parking.id)

    control_file = detector_control_path(db, parking)
    control = read_json(control_file, default={})

    # Для RTSP включаем детекцию автоматически, если конфиг ещё не создан.
    if camera.source_type == CameraSourceType.RTSP.value and not control:
        control = build_detector_config(db, parking, active=True)
        write_json(control_file, control)

    return {
        "parking_id": parking.slug,
        "source_type": camera.source_type,
        "active": bool(control.get("active")),
        "controls_visible": camera.source_type == CameraSourceType.VIDEO.value,
        "control_file": str(control_file),
        "source": control.get("source"),
        "last_error": control.get("last_error"),
        "last_processed_at": control.get("last_processed_at"),
    }


@router.post("/start")
def start_detector(
    parking_id: str,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    parking = resolve_parking(parking_id, db, current_user)
    config = build_detector_config(db, parking, active=True)

    write_json(detector_control_path(db, parking), config)

    return {
        "status": "started",
        "parking_id": parking.slug,
        "source_type": config["source_type"],
    }


@router.post("/stop")
def stop_detector(
    parking_id: str,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    parking = resolve_parking(parking_id, db, current_user)
    control_file = detector_control_path(db, parking)

    control = read_json(control_file, default={})
    control["active"] = False

    write_json(control_file, control)

    return {
        "status": "stopped",
        "parking_id": parking.slug,
    }