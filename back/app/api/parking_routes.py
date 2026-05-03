from pathlib import Path
import json
import re
import shutil
import tempfile
from typing import Annotated, Any

import cv2
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from back.app.api.deps import get_current_active_user, require_admin, assert_same_company_or_super_admin
from back.app.database import get_db
from back.app.models.enums import UserRole, CameraSourceType, CameraStatus
from back.app.models.user import User
from back.app.repositories.camera_repository import CameraRepository
from back.app.repositories.company_repository import CompanyRepository
from back.app.repositories.parking_repository import ParkingRepository
from back.app.schemas.parkings import ParkingCreate, ParkingUpdate, ParkingResponse, ParkingLayoutSave, ParkingMapSave
from back.app.services.parking_layout_storage_service import ParkingLayoutStorageService

router = APIRouter(tags=["parkings"])

DATA_ROOT = Path("/app/data/companies")


def runtime_video_path(parking, suffix: str) -> Path:
    """ASCII-путь для OpenCV.

    На Windows OpenCV часто не открывает/не записывает файлы, если в пути есть
    кириллица. Поэтому видео для runtime-операций кладём в отдельную папку без
    имени парковки.
    """
    safe_suffix = suffix if suffix else ".mp4"
    return DATA_ROOT / "_runtime" / "videos" / f"parking_{parking.id}_test_video{safe_suffix}"


def write_image_unicode_safe(path: str | Path, image) -> None:
    """Сохраняет изображение без cv2.imwrite(path, ...).

    cv2.imwrite может вернуть False на путях с кириллицей. imencode кодирует
    изображение в памяти, а Path.write_bytes уже нормально работает с Unicode.
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
    """Открывает видео/RTSP, обходя проблему OpenCV с Unicode-путями.

    Для URL ничего не меняем. Для локального файла сначала пробуем обычный путь,
    затем при необходимости копируем файл во временный ASCII-путь и открываем его.
    Возвращает (cap, temp_path), где temp_path нужно удалить после release().
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
    repo = CompanyRepository(db)
    company = repo.get_by_id(company_id)

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
    """Создаёт только runtime-пути для старого детектора.

    Источник истины для layout/map/occupancy теперь БД. JSON-файлы нужны только потому,
    что detector_supervisor/detect_parking пока читают и пишут файлы.
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
        parking = repo.get_by_id_or_slug(parking_id, company_id=current_user.company_id)

    if not parking:
        raise HTTPException(status_code=404, detail="Parking not found")

    assert_same_company_or_super_admin(current_user, parking.company_id)
    ensure_parking_files(db, parking)

    db.refresh(parking)
    return parking


def sync_occupancy_from_runtime_file(db: Session, parking) -> None:
    """Подхватывает occupancy.json, который обновляет старый detector_supervisor, и кладёт его в БД."""
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


def summarize_parking(db: Session, parking) -> dict:
    ensure_parking_files(db, parking)
    db.refresh(parking)

    storage = ParkingLayoutStorageService(db)
    sync_occupancy_from_runtime_file(db, parking)

    layout = storage.build_layout_from_db(parking)
    occupancy = storage.build_occupancy_from_db(parking)

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
    }


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
    if source_type not in {CameraSourceType.RTSP.value, CameraSourceType.VIDEO.value, CameraSourceType.IMAGE.value}:
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
    storage.write_runtime_json_files(parking, parking.layout_file_path, parking.occupancy_file_path)

    return summarize_parking(db, parking)


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

    return summarize_parking(db, updated)


@router.delete("/parkings/{parking_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_parking(
    parking_id: str,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    parking = resolve_parking(parking_id, db, current_user)
    parking_db_id = int(parking.id)
    base = parking_storage_dir(db, parking)

    # Удаляем явно, а не только через ORM/cascade.
    # Это чинит ситуацию, когда парковка исчезла с фронта, но связанные строки
    # остались в таблицах из-за отсутствующего/старого FK или soft-delete логики модели.
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
                {"parking_id": parking_db_id, "vertex_ids": vertex_ids},
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

    if base.exists():
        import shutil
        shutil.rmtree(base)


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
    storage.write_runtime_json_files(parking, parking.layout_file_path, parking.occupancy_file_path)

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
    storage.write_runtime_json_files(parking, parking.layout_file_path, parking.occupancy_file_path)

    if parking.map_file_path:
        write_json(parking.map_file_path, storage.build_map_from_db(parking))

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
    file: UploadFile = File(...),
):
    parking = resolve_parking(parking_id, db, current_user)
    camera_repo = CameraRepository(db)

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".mp4", ".avi", ".mov", ".mkv", ".webm"}:
        raise HTTPException(status_code=400, detail="Unsupported video format")

    # Основной runtime-путь делаем ASCII-only, чтобы OpenCV на Windows
    # корректно открывал загруженное видео даже при slug вроде "офис".
    target = runtime_video_path(parking, suffix)
    target.parent.mkdir(parents=True, exist_ok=True)

    with target.open("wb") as output:
        while chunk := await file.read(1024 * 1024):
            output.write(chunk)

    # Дополнительно оставляем копию рядом с парковкой для удобства просмотра файлов.
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

    return {
        "status": "ok",
        "test_video_path": str(target),
        "stored_copy_path": str(legacy_target),
    }


@router.post("/parkings/{parking_id}/snapshot/upload")
async def upload_snapshot(
    parking_id: str,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
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

    return {
        "status": "ok",
        "screenshot_file_path": str(target),
    }


@router.post("/parkings/{parking_id}/snapshot/capture")
def capture_snapshot(
    parking_id: str,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    parking = resolve_parking(parking_id, db, current_user)
    camera_repo = CameraRepository(db)
    camera = camera_repo.get_first_by_parking(parking.id)

    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    source = camera.source_url if camera.source_type == CameraSourceType.RTSP.value else camera.test_video_path

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

        camera_repo.update(camera.id, last_snapshot_path=str(target), status=CameraStatus.ONLINE.value)

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
