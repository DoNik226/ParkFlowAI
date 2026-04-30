from pathlib import Path
import json
import re
from typing import Annotated, Any

import cv2
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from back.app.api.deps import get_current_active_user, require_admin, assert_same_company_or_super_admin
from back.app.database import get_db
from back.app.models.enums import UserRole, CameraSourceType, CameraStatus
from back.app.models.user import User
from back.app.repositories.camera_repository import CameraRepository
from back.app.repositories.company_repository import CompanyRepository
from back.app.repositories.parking_repository import ParkingRepository
from back.app.schemas.parkings import ParkingCreate, ParkingUpdate, ParkingResponse, ParkingLayoutSave, ParkingMapSave

router = APIRouter(tags=["parkings"])

DATA_ROOT = Path("/app/data/companies")


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


def ensure_parking_files(db: Session, parking) -> None:
    base = parking_storage_dir(db, parking)
    base.mkdir(parents=True, exist_ok=True)
    (base / "source").mkdir(parents=True, exist_ok=True)

    layout_path = base / "layout.json"
    map_path = base / "map.json"
    occupancy_path = base / "occupancy.json"

    if not layout_path.exists():
        write_json(layout_path, {
            "parking": {
                "id": parking.slug,
                "db_id": parking.id,
                "name": parking.name,
                "company_id": parking.company_id,
            },
            "camera": {},
            "zones": [],
            "spots": [],
        })

    if not map_path.exists():
        write_json(map_path, {
            "parking": {
                "id": parking.slug,
                "db_id": parking.id,
                "name": parking.name,
                "company_id": parking.company_id,
            },
            "entrances": [],
            "vertices": [],
            "edges": [],
        })

    if not occupancy_path.exists():
        write_json(occupancy_path, {
            "parking_id": parking.slug,
            "parking_db_id": parking.id,
            "parking_name": parking.name,
            "summary": {
                "total": 0,
                "occupied": 0,
                "free": 0,
                "unknown": 0,
            },
            "spots": [],
        })

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


def summarize_parking(db: Session, parking) -> dict:
    ensure_parking_files(db, parking)
    db.refresh(parking)

    layout = read_json(parking.layout_file_path, default={})
    occupancy = read_json(parking.occupancy_file_path, default={})

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

    layout = read_json(parking.layout_file_path)
    layout["camera"] = {
        "id": camera.id,
        "parking_id": parking.slug,
        "parking_db_id": parking.id,
        "name": camera.name,
        "source_type": camera.source_type,
        "source_url": camera.source_url,
    }
    write_json(parking.layout_file_path, layout)

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
    repo = ParkingRepository(db)
    parking = resolve_parking(parking_id, db, current_user)

    base = parking_storage_dir(db, parking)

    repo.delete(parking.id)

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
    return read_json(parking.layout_file_path)


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

    write_json(parking.layout_file_path, layout)

    occupancy = {
        "parking_id": parking.slug,
        "parking_db_id": parking.id,
        "parking_name": parking.name,
        "summary": {
            "total": len(layout.get("spots", [])),
            "occupied": 0,
            "free": len(layout.get("spots", [])),
            "unknown": 0,
        },
        "spots": [
            {
                "spot_id": spot.get("id"),
                "status": "unknown",
                "enabled": spot.get("enabled", True),
                "row": spot.get("row"),
                "col": spot.get("col"),
                "zone": spot.get("zone"),
                "zone_id": spot.get("zone_id"),
                "confidence": None,
                "vehicle": None,
            }
            for spot in layout.get("spots", [])
        ],
    }

    write_json(parking.occupancy_file_path, occupancy)

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
    return read_json(parking.map_file_path)


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

    write_json(parking.map_file_path, map_data)

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
    return read_json(parking.occupancy_file_path)


@router.get("/parkings/{parking_id}/spots")
def get_parking_spots(
    parking_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    parking = resolve_parking(parking_id, db, current_user)
    layout = read_json(parking.layout_file_path)
    occupancy = read_json(parking.occupancy_file_path)

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
    map_data = read_json(parking.map_file_path, default={})

    entrances = map_data.get("entrances")

    if isinstance(entrances, list):
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

    base = parking_storage_dir(db, parking)
    target = base / "source" / f"test_video{suffix}"
    target.parent.mkdir(parents=True, exist_ok=True)

    with target.open("wb") as output:
        while chunk := await file.read(1024 * 1024):
            output.write(chunk)

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

    cap = cv2.VideoCapture(source)
    try:
        if not cap.isOpened():
            raise HTTPException(status_code=400, detail="Cannot open camera source")

        ok, frame = cap.read()
        if not ok or frame is None:
            raise HTTPException(status_code=400, detail="Cannot read frame")

        base = parking_storage_dir(db, parking)
        target = base / "screenshot.jpg"

        if not cv2.imwrite(str(target), frame):
            raise HTTPException(status_code=500, detail="Cannot save snapshot")

        parking_repo = ParkingRepository(db)
        parking_repo.update(parking.id, screenshot_file_path=str(target))

        camera_repo.update(camera.id, last_snapshot_path=str(target), status=CameraStatus.ONLINE.value)

        return {
            "status": "ok",
            "screenshot_file_path": str(target),
        }
    finally:
        cap.release()


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