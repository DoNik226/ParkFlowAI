from pathlib import Path
import json
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/cameras", tags=["cameras"])

DATA_ROOT = Path("/app/data/parkings")


class CameraCreate(BaseModel):
    id: str
    parking_id: str
    name: str | None = None
    source_url: str | None = None
    source_type: str | None = None


class CameraUpdate(BaseModel):
    name: str | None = None
    source_url: str | None = None
    source_type: str | None = None


def safe_id(value: str) -> str:
    normalized = value.replace("_", "").replace("-", "")

    if not normalized.isalnum():
        raise HTTPException(status_code=400, detail="Invalid id")

    return value


def read_json(path: Path):
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path.name}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: Path, data: Any) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")

    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    temp_path.replace(path)


def get_parking_dirs():
    DATA_ROOT.mkdir(parents=True, exist_ok=True)

    return [
        item
        for item in DATA_ROOT.iterdir()
        if item.is_dir() and (item / "layout.json").exists()
    ]


def normalize_camera(parking_id: str, camera: dict[str, Any] | None):
    camera = camera or {}

    return {
        "id": camera.get("id", f"{parking_id}_camera"),
        "parking_id": camera.get("parking_id", parking_id),
        "name": camera.get("name", f"Камера {parking_id}"),
        "source_url": camera.get("source_url") or camera.get("url") or camera.get("source"),
        "source_type": camera.get("source_type") or camera.get("type") or "unknown",
    }


@router.get("")
def list_cameras(parking_id: str | None = Query(default=None)):
    cameras = []

    for parking_dir in get_parking_dirs():
        layout = read_json(parking_dir / "layout.json")
        current_parking_id = layout.get("parking", {}).get("id", parking_dir.name)

        if parking_id and current_parking_id != parking_id:
            continue

        cameras.append(normalize_camera(current_parking_id, layout.get("camera")))

    return cameras


@router.get("/{camera_id}")
def get_camera(camera_id: str):
    for parking_dir in get_parking_dirs():
        layout = read_json(parking_dir / "layout.json")
        parking_id = layout.get("parking", {}).get("id", parking_dir.name)
        camera = normalize_camera(parking_id, layout.get("camera"))

        if camera["id"] == camera_id:
            return camera

    raise HTTPException(status_code=404, detail="Camera not found")


@router.post("", status_code=201)
def create_camera(data: CameraCreate):
    parking_id = safe_id(data.parking_id)
    camera_id = safe_id(data.id)

    parking_dir = DATA_ROOT / parking_id
    layout_file = parking_dir / "layout.json"

    if not layout_file.exists():
        raise HTTPException(status_code=404, detail="Parking not found")

    layout = read_json(layout_file)

    layout["camera"] = {
        "id": camera_id,
        "parking_id": parking_id,
        "name": data.name or f"Камера {parking_id}",
        "source_url": data.source_url,
        "source_type": data.source_type or "unknown",
    }

    write_json(layout_file, layout)

    return normalize_camera(parking_id, layout["camera"])


@router.put("/{camera_id}")
def update_camera(camera_id: str, data: CameraUpdate):
    for parking_dir in get_parking_dirs():
        layout_file = parking_dir / "layout.json"
        layout = read_json(layout_file)
        parking_id = layout.get("parking", {}).get("id", parking_dir.name)
        camera = normalize_camera(parking_id, layout.get("camera"))

        if camera["id"] != camera_id:
            continue

        if data.name is not None:
            camera["name"] = data.name

        if data.source_url is not None:
            camera["source_url"] = data.source_url

        if data.source_type is not None:
            camera["source_type"] = data.source_type

        layout["camera"] = camera
        write_json(layout_file, layout)

        return camera

    raise HTTPException(status_code=404, detail="Camera not found")


@router.delete("/{camera_id}", status_code=204)
def delete_camera(camera_id: str):
    for parking_dir in get_parking_dirs():
        layout_file = parking_dir / "layout.json"
        layout = read_json(layout_file)
        parking_id = layout.get("parking", {}).get("id", parking_dir.name)
        camera = normalize_camera(parking_id, layout.get("camera"))

        if camera["id"] != camera_id:
            continue

        layout["camera"] = {}
        write_json(layout_file, layout)
        return

    raise HTTPException(status_code=404, detail="Camera not found")


@router.post("/{camera_id}/reconnect")
def reconnect_camera(camera_id: str):
    camera = get_camera(camera_id)

    return {
        "camera_id": camera_id,
        "status": "ok",
        "message": "Команда переподключения принята",
        "camera": camera,
    }


@router.get("/{camera_id}/stream")
def get_camera_stream(camera_id: str):
    camera = get_camera(camera_id)

    raise HTTPException(
        status_code=501,
        detail={
            "message": "Поток камеры пока не проксируется через backend",
            "camera": camera,
        },
    )


@router.get("/{camera_id}/snapshot")
def get_camera_snapshot(camera_id: str):
    camera = get_camera(camera_id)

    raise HTTPException(
        status_code=501,
        detail={
            "message": "Snapshot камеры пока не проксируется через backend",
            "camera": camera,
        },
    )