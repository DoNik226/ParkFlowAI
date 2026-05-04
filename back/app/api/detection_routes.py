from pathlib import Path
import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from back.app.api.deps import (
    assert_same_company_or_super_admin,
    get_audit_logger,
    get_current_active_user,
    require_admin,
)
from back.app.database import get_db
from back.app.logger import AuditLogger
from back.app.models.enums import CameraSourceType, UserRole
from back.app.models.user import User
from back.app.repositories.camera_repository import CameraRepository
from back.app.repositories.company_repository import CompanyRepository
from back.app.repositories.parking_repository import ParkingRepository
from back.app.services.parking_layout_storage_service import ParkingLayoutStorageService

router = APIRouter(prefix="/parkings/{parking_id}/detector", tags=["detector"])

DATA_ROOT = Path("/app/data/companies")
DEFAULT_MODEL_PATH = Path("/app/models/best.pt")


def read_json(path: Path, default: Any = None):
    if not path.exists():
        return default

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def make_json_serializable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)

    if isinstance(value, dict):
        return {
            key: make_json_serializable(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            make_json_serializable(item)
            for item in value
        ]

    return value


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = path.with_suffix(path.suffix + ".tmp")
    serializable_data = make_json_serializable(data)

    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(serializable_data, file, ensure_ascii=False, indent=2)

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


def ensure_detector_runtime_files(db: Session, parking) -> None:
    """Перед стартом детектора собирает layout/occupancy JSON из БД.

    detector_supervisor читает layout_path и пишет save_json, поэтому файлы
    остаются runtime-кэшем, но фронт и сохранение могут работать через БД.
    """
    if not parking.layout_file_path:
        raise HTTPException(status_code=400, detail="Layout path is empty")

    if not parking.occupancy_file_path:
        raise HTTPException(status_code=400, detail="Occupancy path is empty")

    ParkingLayoutStorageService(db).write_runtime_json_files(
        parking=parking,
        layout_path=str(parking.layout_file_path),
        occupancy_path=str(parking.occupancy_file_path),
    )


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

    ensure_detector_runtime_files(db, parking)

    return {
        "parking_id": parking.slug,
        "parking_db_id": parking.id,
        "camera_id": camera.id,
        "company_id": parking.company_id,
        "active": active,
        "source_type": source_type,
        "source": str(source),
        "layout_path": str(parking.layout_file_path),
        "save_json": str(parking.occupancy_file_path),
        "save_frame": str(parking.debug_frame_path) if parking.debug_frame_path else None,
        "model": str(DEFAULT_MODEL_PATH),
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
    control = read_json(control_file, default={}) or {}

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
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
):
    parking = resolve_parking(parking_id, db, current_user)
    config = build_detector_config(db, parking, active=True)

    write_json(detector_control_path(db, parking), config)
    audit_logger.log_admin_action(
        current_user.id,
        "Администратор запустил детекцию",
        parking_id=parking.id,
        details={
            "parking_slug": parking.slug,
            "camera_id": config["camera_id"],
            "source_type": config["source_type"],
            "source": config["source"],
        },
    )

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
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
):
    parking = resolve_parking(parking_id, db, current_user)
    control_file = detector_control_path(db, parking)

    control = read_json(control_file, default={}) or {}
    control["active"] = False

    write_json(control_file, control)
    audit_logger.log_admin_action(
        current_user.id,
        "Администратор остановил детекцию",
        parking_id=parking.id,
        details={
            "parking_slug": parking.slug,
            "camera_id": control.get("camera_id"),
            "source_type": control.get("source_type"),
        },
    )

    return {
        "status": "stopped",
        "parking_id": parking.slug,
    }
