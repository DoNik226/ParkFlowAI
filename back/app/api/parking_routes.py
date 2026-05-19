from pathlib import Path
import json
import re
import shutil
import tempfile
import time
from typing import Annotated, Any

import cv2
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from back.app.api.deps import (
    assert_same_company_or_super_admin,
    get_audit_logger,
    get_current_active_user,
    require_admin,
)
from back.app.core.security import decode_access_token
from back.app.database import get_db
from back.app.logger import AuditLogger
from back.app.models.enums import UserRole, CameraSourceType, CameraStatus
from back.app.models.user import User
from back.app.repositories.camera_repository import CameraRepository
from back.app.repositories.company_repository import CompanyRepository
from back.app.repositories.parking_repository import ParkingRepository
from back.app.repositories.user_repository import UserRepository
from back.app.schemas.parkings import (
    ParkingCreate,
    ParkingUpdate,
    ParkingResponse,
    ParkingLayoutSave,
    ParkingMapSave,
)
from back.app.services.parking_layout_storage_service import ParkingLayoutStorageService


router = APIRouter(tags=["parkings"])

DATA_ROOT = Path("/app/data/companies")


def runtime_video_path(parking, suffix: str) -> Path:
    """
    ASCII-путь для OpenCV.

    На Windows/OpenCV иногда бывают проблемы с путями, где есть кириллица.
    Поэтому тестовое видео для runtime-операций кладём в отдельную папку.
    """
    safe_suffix = suffix if suffix else ".mp4"
    return DATA_ROOT / "_runtime" / "videos" / f"parking_{parking.id}_test_video{safe_suffix}"


def write_image_unicode_safe(path: str | Path, image) -> None:
    """
    Безопасное сохранение изображения.

    cv2.imwrite может некорректно работать с Unicode-путями.
    Поэтому изображение кодируется в памяти и сохраняется через Path.write_bytes().
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    suffix = target.suffix.lower() or ".jpg"

    if suffix == ".jpeg":
        encode_ext = ".jpg"
    elif suffix in {".jpg", ".png", ".webp", ".bmp"}:
        encode_ext = suffix
    else:
        encode_ext = ".jpg"

    ok, encoded = cv2.imencode(encode_ext, image)

    if not ok:
        raise HTTPException(status_code=500, detail="Cannot encode snapshot")

    target.write_bytes(encoded.tobytes())


def open_video_capture_unicode_safe(source: str):
    """
    Открывает видео/RTSP.

    Для URL ничего не меняется.
    Для локального файла сначала пробуем открыть как есть.
    Если OpenCV не смог открыть файл, копируем его во временный ASCII-путь.
    """
    source_text = str(source)

    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", source_text):
        return cv2.VideoCapture(source_text), None

    cap = cv2.VideoCapture(source_text)

    if cap.isOpened():
        return cap, None

    cap.release()

    source_path = Path(source_text)

    if not source_path.exists():
        return cv2.VideoCapture(source_text), None

    suffix = source_path.suffix or ".mp4"
    temp = tempfile.NamedTemporaryFile(prefix="parkflow_video_", suffix=suffix, delete=False)
    temp_path = Path(temp.name)
    temp.close()

    shutil.copyfile(source_path, temp_path)

    cap = cv2.VideoCapture(str(temp_path))
    return cap, temp_path


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-zа-я0-9]+", "_", value, flags=re.IGNORECASE)
    value = value.strip("_")

    return value or "parking"


def safe_name(value: str) -> str:
    normalized = value.replace("_", "").replace("-", "")

    if not normalized.isalnum():
        raise HTTPException(status_code=400, detail="Invalid identifier")

    return value


def get_company_slug(db: Session, company_id: int) -> str:
    company = CompanyRepository(db).get_by_id(company_id)

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    return company.slug


def parking_storage_dir(db: Session, parking) -> Path:
    company_slug = get_company_slug(db, parking.company_id)
    return DATA_ROOT / company_slug / "parkings" / parking.slug


def read_json(path: str | Path, default: Any = None):
    path = Path(path)

    if not path.exists():
        if default is not None:
            return default

        raise HTTPException(status_code=404, detail=f"File not found: {path.name}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: str | Path, data: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp = path.with_suffix(path.suffix + ".tmp")

    with tmp.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    tmp.replace(path)


def ensure_parking_files(db: Session, parking) -> None:
    """
    Создаёт runtime-пути для layout/map/occupancy/debug-frame.

    Основные данные хранятся в БД, но detector использует runtime JSON-файлы.
    """
    base = parking_storage_dir(db, parking)
    base.mkdir(parents=True, exist_ok=True)
    (base / "source").mkdir(parents=True, exist_ok=True)

    layout_path = base / "layout.json"
    map_path = base / "map.json"
    occupancy_path = base / "occupancy.json"

    update_data = {}

    if not parking.layout_file_path:
        update_data["layout_file_path"] = str(layout_path)

    if not parking.map_file_path:
        update_data["map_file_path"] = str(map_path)

    if not parking.occupancy_file_path:
        update_data["occupancy_file_path"] = str(occupancy_path)

    if not parking.debug_frame_path:
        update_data["debug_frame_path"] = str(base / "debug_detection.jpg")

    if update_data:
        repo = ParkingRepository(db)
        repo.update(parking.id, **update_data)
        db.refresh(parking)


def resolve_parking(
    parking_id: str,
    db: Session,
    current_user: User,
):
    repo = ParkingRepository(db)

    if current_user.role == UserRole.SUPER_ADMIN.value:
        parking = repo.get_by_id_or_slug(parking_id)
    else:
        parking = repo.get_by_id_or_slug(
            parking_id,
            company_id=current_user.company_id,
        )

    if not parking:
        raise HTTPException(status_code=404, detail="Parking not found")

    assert_same_company_or_super_admin(current_user, parking.company_id)
    ensure_parking_files(db, parking)

    db.refresh(parking)

    return parking


def sync_occupancy_from_runtime_file(db: Session, parking) -> None:
    """
    Подхватывает occupancy.json, который обновляет detector, и синхронизирует его с БД.
    """
    if not parking.occupancy_file_path:
        return

    path = Path(parking.occupancy_file_path)

    if not path.exists():
        return

    try:
        occupancy = read_json(path, default=None)
    except Exception:
        return

    if isinstance(occupancy, dict) and isinstance(occupancy.get("spots"), list):
        ParkingLayoutStorageService(db).save_occupancy_to_db(parking.id, occupancy)


def get_user_from_token(token: str, db: Session) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_exception

        user = UserRepository(db).get_by_id(int(user_id))
    except Exception:
        raise credentials_exception

    if user is None or not user.is_active:
        raise credentials_exception

    return user


def get_user_from_header_or_query_token(
    request: Request,
    db: Session,
    token: str | None = None,
) -> User:
    """
    Авторизация для media endpoint-ов.

    Axios умеет отправлять Authorization: Bearer <token>.
    А <video>, <img> и MJPEG-потоки не умеют удобно добавлять такой header.
    Поэтому для них разрешаем токен в query-параметре: ?token=...
    """
    raw_token = token

    if not raw_token:
        authorization = request.headers.get("Authorization", "")

        if authorization.startswith("Bearer "):
            raw_token = authorization.replace("Bearer ", "", 1).strip()

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    return get_user_from_token(raw_token, db)


def get_source_camera_or_404(db: Session, parking):
    camera = CameraRepository(db).get_first_by_parking(parking.id)

    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    return camera


def serialize_camera(camera) -> dict | None:
    if not camera:
        return None

    return {
        "id": camera.id,
        "parking_id": camera.parking_id,
        "name": camera.name,
        "source_type": camera.source_type,
        "source_url": camera.source_url,
        "test_video_path": camera.test_video_path,
        "status": camera.status,
        "is_active": camera.is_active,
        "last_snapshot_path": camera.last_snapshot_path,
    }


def summarize_parking(db: Session, parking) -> dict:
    ensure_parking_files(db, parking)
    db.refresh(parking)

    storage = ParkingLayoutStorageService(db)
    sync_occupancy_from_runtime_file(db, parking)

    layout = storage.build_layout_from_db(parking)
    occupancy = storage.build_occupancy_from_db(parking)

    camera_repo = CameraRepository(db)
    cameras = camera_repo.get_by_parking(parking.id)

    serialized_cameras = [
        serialize_camera(camera)
        for camera in cameras
        if camera is not None
    ]

    first_camera = serialized_cameras[0] if serialized_cameras else None

    return {
        "id": parking.slug,
        "db_id": parking.id,
        "company_id": parking.company_id,
        "name": parking.name,
        "slug": parking.slug,
        "description": parking.description,
        "is_active": parking.is_active,
        "layout_file_path": parking.layout_file_path,
        "map_file_path": parking.map_file_path,
        "occupancy_file_path": parking.occupancy_file_path,
        "screenshot_file_path": parking.screenshot_file_path,
        "debug_frame_path": parking.debug_frame_path,
        "spots_count": len(layout.get("spots", [])),
        "zones_count": len(layout.get("zones", [])),
        "summary": occupancy.get("summary", {}),
        "camera": first_camera,
        "cameras": serialized_cameras,
        "camera_id": first_camera.get("id") if first_camera else None,
        "camera_name": first_camera.get("name") if first_camera else None,
        "source_type": first_camera.get("source_type") if first_camera else None,
        "source_url": first_camera.get("source_url") if first_camera else None,
        "test_video_path": first_camera.get("test_video_path") if first_camera else None,
        "camera_status": first_camera.get("status") if first_camera else None,
    }


def guess_video_media_type(path: str | Path) -> str:
    suffix = Path(path).suffix.lower()

    if suffix == ".webm":
        return "video/webm"

    if suffix == ".mov":
        return "video/quicktime"

    if suffix == ".avi":
        return "video/x-msvideo"

    if suffix == ".mkv":
        return "video/x-matroska"

    return "video/mp4"


def mjpeg_frame_generator(source: str, loop: bool = True, fps: float = 15.0):
    """
    Отдаёт видео/RTSP как MJPEG-поток.

    Важно:
    - не используем cv2.waitKey(), потому что backend работает без GUI;
    - не выбрасываем HTTPException внутри generator после старта ответа;
    - при конце тестового видео перематываемся в начало.
    """
    delay_sec = 1.0 / max(fps, 1.0)

    cap, temp_source_path = open_video_capture_unicode_safe(source)

    try:
        while True:
            if not cap.isOpened():
                break

            ok, frame = cap.read()

            if not ok or frame is None:
                if loop:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    time.sleep(delay_sec)
                    continue

                break

            ok, encoded = cv2.imencode(".jpg", frame)

            if not ok:
                time.sleep(delay_sec)
                continue

            frame_bytes = encoded.tobytes()

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n"
                b"Cache-Control: no-cache\r\n"
                b"Pragma: no-cache\r\n\r\n"
                + frame_bytes
                + b"\r\n"
            )

            time.sleep(delay_sec)

    finally:
        cap.release()

        if temp_source_path is not None:
            try:
                Path(temp_source_path).unlink(missing_ok=True)
            except Exception:
                pass


@router.get("/parkings", response_model=list[ParkingResponse])
def list_parkings(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    repo = ParkingRepository(db)

    if current_user.role == UserRole.SUPER_ADMIN.value:
        parkings = repo.list_all_active(limit=1000)
    else:
        if current_user.company_id is None:
            return []

        parkings = repo.list_for_company(current_user.company_id, limit=1000)

    return [summarize_parking(db, parking) for parking in parkings]


@router.post("/parkings", response_model=ParkingResponse, status_code=status.HTTP_201_CREATED)
def create_parking(
    data: ParkingCreate,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
):
    parking_repo = ParkingRepository(db)
    camera_repo = CameraRepository(db)

    company_id = data.company_id

    if current_user.role != UserRole.SUPER_ADMIN.value:
        company_id = current_user.company_id

    if company_id is None:
        raise HTTPException(status_code=400, detail="company_id is required")

    assert_same_company_or_super_admin(current_user, company_id)

    slug = safe_name(data.slug or slugify(data.name))

    if parking_repo.slug_exists(company_id, slug):
        raise HTTPException(status_code=409, detail="Parking slug already exists")

    parking = parking_repo.create(
        company_id=company_id,
        name=data.name,
        slug=slug,
        description=data.description,
        is_active=True,
    )

    ensure_parking_files(db, parking)
    db.refresh(parking)

    camera_name = data.camera_name or f"Камера {parking.name}"

    source_type = data.source_type or CameraSourceType.RTSP.value

    if source_type not in {
        CameraSourceType.RTSP.value,
        CameraSourceType.VIDEO.value,
        CameraSourceType.IMAGE.value,
    }:
        raise HTTPException(status_code=400, detail="Invalid source_type")

    camera = camera_repo.create(
        parking_id=parking.id,
        name=camera_name,
        source_type=source_type,
        source_url=data.source_url,
        status=CameraStatus.OFFLINE.value,
        is_active=True,
    )

    initial_layout = {
        "parking": {
            "id": parking.slug,
            "db_id": parking.id,
            "name": parking.name,
            "company_id": parking.company_id,
        },
        "camera": {
            "id": camera.id,
            "parking_id": parking.slug,
            "parking_db_id": parking.id,
            "name": camera.name,
            "source_type": camera.source_type,
            "source_url": camera.source_url,
            "test_video_path": camera.test_video_path,
        },
        "zones": [],
        "spots": [],
    }

    storage = ParkingLayoutStorageService(db)
    storage.save_layout_to_db(parking, initial_layout)
    storage.write_runtime_json_files(
        parking,
        parking.layout_file_path,
        parking.occupancy_file_path,
    )

    result = summarize_parking(db, parking)

    audit_logger.log_admin_action(
        current_user.id,
        "Администратор создал парковку",
        parking_id=parking.id,
        details={
            "parking_slug": parking.slug,
            "parking_name": parking.name,
            "camera_id": camera.id,
            "camera_name": camera.name,
            "source_type": camera.source_type,
        },
    )

    return result


@router.get("/parkings/{parking_id}", response_model=ParkingResponse)
def get_parking(
    parking_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    parking = resolve_parking(parking_id, db, current_user)

    return summarize_parking(db, parking)


@router.put("/parkings/{parking_id}", response_model=ParkingResponse)
def update_parking(
    parking_id: str,
    data: ParkingUpdate,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
):
    repo = ParkingRepository(db)
    parking = resolve_parking(parking_id, db, current_user)

    update_data = data.model_dump(exclude_unset=True)

    if "slug" in update_data and update_data["slug"]:
        new_slug = safe_name(update_data["slug"])

        if repo.slug_exists(parking.company_id, new_slug, exclude_parking_id=parking.id):
            raise HTTPException(status_code=409, detail="Parking slug already exists")

        update_data["slug"] = new_slug

    updated = repo.update(parking.id, **update_data)

    audit_logger.log_admin_action(
        current_user.id,
        "Администратор обновил парковку",
        parking_id=updated.id,
        details={
            "parking_slug": updated.slug,
            "parking_name": updated.name,
            "updated_fields": sorted(update_data.keys()),
        },
    )

    return summarize_parking(db, updated)


@router.delete("/parkings/{parking_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_parking(
    parking_id: str,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
):
    parking = resolve_parking(parking_id, db, current_user)

    parking_db_id = int(parking.id)
    parking_slug = str(parking.slug)
    parking_name = str(parking.name)
    parking_base = parking_storage_dir(db, parking)

    deleted_parking_details = {
        "deleted_parking_id": parking_db_id,
        "deleted_parking_slug": parking_slug,
        "deleted_parking_name": parking_name,
    }

    try:
        vertex_ids = [
            row[0]
            for row in db.execute(
                text("SELECT id FROM road_vertices WHERE parking_id = :parking_id"),
                {"parking_id": parking_db_id},
            ).all()
        ]

        db.execute(
            text(
                """
                UPDATE parking_spots
                SET road_vertex_id = NULL
                WHERE parking_id = :parking_id
                """
            ),
            {"parking_id": parking_db_id},
        )

        if vertex_ids:
            db.execute(
                text(
                    """
                    DELETE FROM road_edges
                    WHERE parking_id = :parking_id
                       OR source = ANY(:vertex_ids)
                       OR destination = ANY(:vertex_ids)
                    """
                ),
                {
                    "parking_id": parking_db_id,
                    "vertex_ids": vertex_ids,
                },
            )
        else:
            db.execute(
                text("DELETE FROM road_edges WHERE parking_id = :parking_id"),
                {"parking_id": parking_db_id},
            )

        for sql in [
            "DELETE FROM entrances WHERE parking_id = :parking_id",
            "DELETE FROM parking_occupancy_cache WHERE parking_id = :parking_id",
            "DELETE FROM parking_spots WHERE parking_id = :parking_id",
            "DELETE FROM cameras WHERE parking_id = :parking_id",
            "DELETE FROM road_vertices WHERE parking_id = :parking_id",
            "DELETE FROM parkings WHERE id = :parking_id",
        ]:
            db.execute(text(sql), {"parking_id": parking_db_id})

        db.commit()
    except Exception:
        db.rollback()
        raise

    if parking_base.exists():
        shutil.rmtree(parking_base)

    audit_logger.log_admin_action(
        current_user.id,
        "Администратор удалил парковку",
        parking_id=None,
        details=deleted_parking_details,
    )


@router.get("/parkings/{parking_id}/layout")
def get_layout(
    parking_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    parking = resolve_parking(parking_id, db, current_user)

    return ParkingLayoutStorageService(db).build_layout_from_db(parking)


@router.put("/parkings/{parking_id}/layout")
def save_layout(
    parking_id: str,
    data: ParkingLayoutSave,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
):
    parking = resolve_parking(parking_id, db, current_user)

    layout = data.layout

    layout.setdefault("parking", {})
    layout["parking"]["id"] = parking.slug
    layout["parking"]["db_id"] = parking.id
    layout["parking"]["name"] = parking.name
    layout["parking"]["company_id"] = parking.company_id

    camera_repo = CameraRepository(db)
    camera = camera_repo.get_first_by_parking(parking.id)

    if camera:
        layout["camera"] = {
            "id": camera.id,
            "parking_id": parking.slug,
            "parking_db_id": parking.id,
            "name": camera.name,
            "source_type": camera.source_type,
            "source_url": camera.source_url,
            "test_video_path": camera.test_video_path,
        }
    else:
        layout["camera"] = {
            "id": None,
            "parking_id": parking.slug,
            "parking_db_id": parking.id,
            "name": None,
            "source_type": None,
            "source_url": None,
            "test_video_path": None,
        }

    storage = ParkingLayoutStorageService(db)
    storage.save_layout_to_db(parking, layout)
    storage.write_runtime_json_files(
        parking,
        parking.layout_file_path,
        parking.occupancy_file_path,
    )

    audit_logger.log_admin_action(
        current_user.id,
        "Администратор сохранил разметку парковки",
        parking_id=parking.id,
        details={
            "parking_slug": parking.slug,
            "zones_count": len(layout.get("zones", [])),
            "spots_count": len(layout.get("spots", [])),
            "camera_id": camera.id if camera else None,
        },
    )

    return {
        "status": "ok",
        "parking": summarize_parking(db, parking),
    }


@router.get("/parkings/{parking_id}/map")
def get_map(
    parking_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    parking = resolve_parking(parking_id, db, current_user)

    return ParkingLayoutStorageService(db).build_map_from_db(parking)


@router.put("/parkings/{parking_id}/map")
def save_map(
    parking_id: str,
    data: ParkingMapSave,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
):
    parking = resolve_parking(parking_id, db, current_user)

    map_data = data.map

    map_data.setdefault("parking", {})
    map_data["parking"]["id"] = parking.slug
    map_data["parking"]["db_id"] = parking.id
    map_data["parking"]["name"] = parking.name
    map_data["parking"]["company_id"] = parking.company_id

    storage = ParkingLayoutStorageService(db)
    storage.save_map_to_db(parking, map_data)
    storage.write_runtime_json_files(
        parking,
        parking.layout_file_path,
        parking.occupancy_file_path,
    )

    if parking.map_file_path:
        write_json(parking.map_file_path, storage.build_map_from_db(parking))

    audit_logger.log_admin_action(
        current_user.id,
        "Администратор сохранил карту парковки",
        parking_id=parking.id,
        details={
            "parking_slug": parking.slug,
            "roads_count": len(map_data.get("roads", [])),
            "entrances_count": len(map_data.get("entrances", [])),
            "labels_count": len(map_data.get("labels", [])),
        },
    )

    return {
        "status": "ok",
        "parking": summarize_parking(db, parking),
    }


@router.get("/parkings/{parking_id}/occupancy")
def get_occupancy(
    parking_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    parking = resolve_parking(parking_id, db, current_user)
    sync_occupancy_from_runtime_file(db, parking)

    return ParkingLayoutStorageService(db).build_occupancy_from_db(parking)


@router.get("/parkings/{parking_id}/spots")
def get_parking_spots(
    parking_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    parking = resolve_parking(parking_id, db, current_user)
    sync_occupancy_from_runtime_file(db, parking)

    storage = ParkingLayoutStorageService(db)
    layout = storage.build_layout_from_db(parking)
    occupancy = storage.build_occupancy_from_db(parking)

    status_by_id = {
        item.get("spot_id"): item
        for item in occupancy.get("spots", [])
    }

    return [
        {
            **spot,
            "status": status_by_id.get(spot.get("id"), {}).get("status", "unknown"),
            "confidence": status_by_id.get(spot.get("id"), {}).get("confidence"),
            "vehicle": status_by_id.get(spot.get("id"), {}).get("vehicle"),
        }
        for spot in layout.get("spots", [])
    ]


@router.get("/parkings/{parking_id}/free-spots")
def get_free_spots(
    parking_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    spots = get_parking_spots(parking_id, current_user, db)
    free_spots = [spot for spot in spots if spot.get("status") == "free"]

    return {
        "parking_id": parking_id,
        "spots": free_spots,
        "total": len(free_spots),
    }


@router.get("/parkings/{parking_id}/entrances")
def get_entrances(
    parking_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    parking = resolve_parking(parking_id, db, current_user)
    map_data = ParkingLayoutStorageService(db).build_map_from_db(parking)

    entrances = map_data.get("entrances")

    if isinstance(entrances, list) and entrances:
        return entrances

    return [
        {
            "id": "1",
            "name": "Въезд 1",
            "parking_id": parking.slug,
        }
    ]


@router.post("/parkings/{parking_id}/source-video")
async def upload_source_video(
    parking_id: str,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
    file: UploadFile = File(...),
):
    parking = resolve_parking(parking_id, db, current_user)
    camera_repo = CameraRepository(db)

    suffix = Path(file.filename or "").suffix.lower()

    if suffix not in {".mp4", ".avi", ".mov", ".mkv", ".webm"}:
        raise HTTPException(status_code=400, detail="Unsupported video format")

    target = runtime_video_path(parking, suffix)
    target.parent.mkdir(parents=True, exist_ok=True)

    with target.open("wb") as output:
        while chunk := await file.read(1024 * 1024):
            output.write(chunk)

    base = parking_storage_dir(db, parking)
    legacy_target = base / "source" / f"test_video{suffix}"
    legacy_target.parent.mkdir(parents=True, exist_ok=True)

    if legacy_target != target:
        shutil.copyfile(target, legacy_target)

    camera = camera_repo.get_first_by_parking(parking.id)

    if camera:
        camera_repo.update(
            camera.id,
            source_type=CameraSourceType.VIDEO.value,
            test_video_path=str(target),
            source_url=None,
        )

    audit_logger.log_admin_action(
        current_user.id,
        "Администратор загрузил тестовое видео",
        parking_id=parking.id,
        details={
            "parking_slug": parking.slug,
            "camera_id": camera.id if camera else None,
            "filename": file.filename,
            "test_video_path": str(target),
        },
    )

    return {
        "status": "ok",
        "test_video_path": str(target),
        "stored_copy_path": str(legacy_target),
    }


@router.delete("/parkings/{parking_id}/source-video")
def delete_source_video(
    parking_id: str,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
):
    parking = resolve_parking(parking_id, db, current_user)
    camera_repo = CameraRepository(db)
    camera = camera_repo.get_first_by_parking(parking.id)

    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    deleted_files = []

    if camera.test_video_path:
        video_path = Path(camera.test_video_path)

        if video_path.exists() and video_path.is_file():
            video_path.unlink()
            deleted_files.append(str(video_path))

    base = parking_storage_dir(db, parking)
    source_dir = base / "source"

    if source_dir.exists():
        for file_path in source_dir.glob("test_video.*"):
            if file_path.is_file():
                file_path.unlink()
                deleted_files.append(str(file_path))

    control_file = base / "detector_control.json"

    if control_file.exists():
        try:
            control = read_json(control_file, default={}) or {}
            control["active"] = False
            control["last_error"] = "Test video was deleted"
            write_json(control_file, control)
        except Exception:
            pass

    update_data = {
        "test_video_path": None,
    }

    if camera.source_url:
        update_data["source_type"] = CameraSourceType.RTSP.value
    else:
        update_data["source_type"] = CameraSourceType.VIDEO.value

    camera_repo.update(camera.id, **update_data)

    audit_logger.log_admin_action(
        current_user.id,
        "Администратор удалил тестовое видео",
        parking_id=parking.id,
        details={
            "parking_slug": parking.slug,
            "camera_id": camera.id,
            "deleted_files": deleted_files,
        },
    )

    return {
        "status": "ok",
        "parking_id": parking.slug,
        "deleted_files": deleted_files,
    }


@router.post("/parkings/{parking_id}/snapshot/upload")
async def upload_snapshot(
    parking_id: str,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
    file: UploadFile = File(...),
):
    parking = resolve_parking(parking_id, db, current_user)

    suffix = Path(file.filename or "").suffix.lower()

    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(status_code=400, detail="Unsupported image format")

    base = parking_storage_dir(db, parking)
    target = base / "screenshot.jpg"

    with target.open("wb") as output:
        while chunk := await file.read(1024 * 1024):
            output.write(chunk)

    repo = ParkingRepository(db)
    repo.update(parking.id, screenshot_file_path=str(target))

    audit_logger.log_admin_action(
        current_user.id,
        "Администратор загрузил snapshot парковки",
        parking_id=parking.id,
        details={
            "parking_slug": parking.slug,
            "filename": file.filename,
            "screenshot_file_path": str(target),
        },
    )

    return {
        "status": "ok",
        "screenshot_file_path": str(target),
    }


@router.post("/parkings/{parking_id}/snapshot/capture")
def capture_snapshot(
    parking_id: str,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
):
    parking = resolve_parking(parking_id, db, current_user)
    camera_repo = CameraRepository(db)
    camera = camera_repo.get_first_by_parking(parking.id)

    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    source = (
        camera.source_url
        if camera.source_type == CameraSourceType.RTSP.value
        else camera.test_video_path
    )

    if not source:
        raise HTTPException(status_code=400, detail="Camera source is empty")

    cap, temp_source_path = open_video_capture_unicode_safe(source)

    try:
        if not cap.isOpened():
            raise HTTPException(status_code=400, detail="Cannot open camera source")

        ok, frame = cap.read()

        if not ok or frame is None:
            raise HTTPException(status_code=400, detail="Cannot read frame")

        base = parking_storage_dir(db, parking)
        target = base / "screenshot.jpg"

        write_image_unicode_safe(target, frame)

        parking_repo = ParkingRepository(db)
        parking_repo.update(parking.id, screenshot_file_path=str(target))

        camera_repo.update(
            camera.id,
            last_snapshot_path=str(target),
            status=CameraStatus.ONLINE.value,
        )

        audit_logger.log_admin_action(
            current_user.id,
            "Администратор сохранил snapshot с камеры",
            parking_id=parking.id,
            details={
                "parking_slug": parking.slug,
                "camera_id": camera.id,
                "camera_name": camera.name,
                "screenshot_file_path": str(target),
            },
        )

        return {
            "status": "ok",
            "screenshot_file_path": str(target),
        }

    finally:
        cap.release()

        if temp_source_path is not None:
            try:
                Path(temp_source_path).unlink(missing_ok=True)
            except Exception:
                pass


@router.get("/parkings/{parking_id}/snapshot")
def get_snapshot(
    parking_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    parking = resolve_parking(parking_id, db, current_user)

    if not parking.screenshot_file_path or not Path(parking.screenshot_file_path).exists():
        raise HTTPException(status_code=404, detail="Snapshot not found")

    return FileResponse(parking.screenshot_file_path)


@router.get("/parkings/{parking_id}/source-video/view")
def view_source_video(
    parking_id: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    token: str | None = Query(default=None),
):
    current_user = get_user_from_header_or_query_token(request, db, token)
    parking = resolve_parking(parking_id, db, current_user)
    camera = get_source_camera_or_404(db, parking)

    if camera.source_type != CameraSourceType.VIDEO.value:
        raise HTTPException(status_code=400, detail="Parking source is not video")

    if not camera.test_video_path:
        raise HTTPException(status_code=404, detail="Video file is not configured")

    video_path = Path(camera.test_video_path)

    if not video_path.exists() or not video_path.is_file():
        raise HTTPException(status_code=404, detail="Video file not found")

    return FileResponse(
        str(video_path),
        media_type=guess_video_media_type(video_path),
        filename=video_path.name,
    )


@router.get("/parkings/{parking_id}/source-video/stream.mjpg")
def view_source_video_stream(
    parking_id: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    token: str | None = Query(default=None),
):
    current_user = get_user_from_header_or_query_token(request, db, token)
    parking = resolve_parking(parking_id, db, current_user)
    camera = get_source_camera_or_404(db, parking)

    if camera.source_type != CameraSourceType.VIDEO.value:
        raise HTTPException(status_code=400, detail="Parking source is not video")

    if not camera.test_video_path:
        raise HTTPException(status_code=404, detail="Video file is not configured")

    video_path = Path(camera.test_video_path)

    if not video_path.exists() or not video_path.is_file():
        raise HTTPException(status_code=404, detail="Video file not found")

    # Проверяем до StreamingResponse, чтобы браузер не получил оборванный chunked-response.
    test_cap, temp_source_path = open_video_capture_unicode_safe(str(video_path))

    try:
        if not test_cap.isOpened():
            raise HTTPException(status_code=400, detail="Cannot open video file")

        ok, frame = test_cap.read()

        if not ok or frame is None:
            raise HTTPException(status_code=400, detail="Cannot read video frame")

    finally:
        test_cap.release()

        if temp_source_path is not None:
            try:
                Path(temp_source_path).unlink(missing_ok=True)
            except Exception:
                pass

    return StreamingResponse(
        mjpeg_frame_generator(str(video_path), loop=True, fps=15.0),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@router.get("/parkings/{parking_id}/camera-stream.mjpg")
def view_camera_stream(
    parking_id: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    token: str | None = Query(default=None),
):
    current_user = get_user_from_header_or_query_token(request, db, token)
    parking = resolve_parking(parking_id, db, current_user)
    camera = get_source_camera_or_404(db, parking)

    if camera.source_type != CameraSourceType.RTSP.value:
        raise HTTPException(status_code=400, detail="Parking source is not RTSP stream")

    if not camera.source_url:
        raise HTTPException(status_code=404, detail="RTSP URL is not configured")

    test_cap, temp_source_path = open_video_capture_unicode_safe(camera.source_url)

    try:
        if not test_cap.isOpened():
            raise HTTPException(status_code=400, detail="Cannot open RTSP stream")

    finally:
        test_cap.release()

        if temp_source_path is not None:
            try:
                Path(temp_source_path).unlink(missing_ok=True)
            except Exception:
                pass

    return StreamingResponse(
        mjpeg_frame_generator(camera.source_url, loop=False, fps=15.0),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@router.get("/parkings/{parking_id}/debug-frame")
def get_debug_frame(
    parking_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    parking = resolve_parking(parking_id, db, current_user)

    if not parking.debug_frame_path or not Path(parking.debug_frame_path).exists():
        raise HTTPException(status_code=404, detail="Debug frame not found")

    return FileResponse(parking.debug_frame_path)