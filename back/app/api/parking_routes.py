from pathlib import Path
import json
import shutil
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(tags=["parkings"])

DATA_ROOT = Path("/app/data/parkings")


class ParkingCreate(BaseModel):
    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    camera: dict[str, Any] | None = None


class ParkingUpdate(BaseModel):
    name: str | None = None
    camera: dict[str, Any] | None = None


class SpotStatusUpdate(BaseModel):
    status: str


def safe_parking_id(parking_id: str) -> str:
    normalized = parking_id.replace("_", "").replace("-", "")

    if not normalized.isalnum():
        raise HTTPException(status_code=400, detail="Invalid parking_id")

    return parking_id


def get_parking_dir(parking_id: str) -> Path:
    parking_id = safe_parking_id(parking_id)
    path = DATA_ROOT / parking_id

    if not path.exists():
        raise HTTPException(status_code=404, detail="Parking not found")

    return path


def read_json(path: Path, default: Any = None):
    if not path.exists():
        if default is not None:
            return default
        raise HTTPException(status_code=404, detail=f"File not found: {path.name}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = path.with_suffix(path.suffix + ".tmp")

    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    temp_path.replace(path)


def layout_path(parking_id: str) -> Path:
    return get_parking_dir(parking_id) / "layout.json"


def occupancy_path(parking_id: str) -> Path:
    return get_parking_dir(parking_id) / "occupancy.json"


def get_layout(parking_id: str):
    return read_json(layout_path(parking_id))


def get_occupancy(parking_id: str):
    return read_json(
        occupancy_path(parking_id),
        default={
            "parking_id": parking_id,
            "summary": {
                "total": 0,
                "occupied": 0,
                "free": 0,
                "unknown": 0,
            },
            "spots": [],
        },
    )


def summarize_parking(parking_id: str) -> dict[str, Any]:
    layout = get_layout(parking_id)
    occupancy = get_occupancy(parking_id)

    parking = layout.get("parking", {})

    return {
        "id": parking.get("id", parking_id),
        "name": parking.get("name", parking_id),
        "camera": layout.get("camera"),
        "summary": occupancy.get("summary", {}),
        "spots_count": len(layout.get("spots", [])),
        "zones_count": len(layout.get("zones", [])),
    }


@router.get("/parkings")
def list_parkings():
    DATA_ROOT.mkdir(parents=True, exist_ok=True)

    items = []

    for item in sorted(DATA_ROOT.iterdir()):
        if not item.is_dir():
            continue

        layout_file = item / "layout.json"
        if not layout_file.exists():
            continue

        try:
            items.append(summarize_parking(item.name))
        except Exception:
            continue

    return items


@router.get("/parkings/{parking_id}")
def get_parking(parking_id: str):
    return summarize_parking(parking_id)


@router.post("/parkings", status_code=201)
def create_parking(data: ParkingCreate):
    parking_id = safe_parking_id(data.id)
    base = DATA_ROOT / parking_id

    if base.exists():
        raise HTTPException(status_code=409, detail="Parking already exists")

    base.mkdir(parents=True, exist_ok=False)

    layout = {
        "parking": {
            "id": parking_id,
            "name": data.name,
        },
        "camera": data.camera or {
            "id": f"{parking_id}_camera",
            "parking_id": parking_id,
            "name": f"Камера {data.name}",
        },
        "zones": [],
        "spots": [],
    }

    occupancy = {
        "parking_id": parking_id,
        "parking_name": data.name,
        "summary": {
            "total": 0,
            "occupied": 0,
            "free": 0,
            "unknown": 0,
        },
        "spots": [],
    }

    write_json(base / "layout.json", layout)
    write_json(base / "occupancy.json", occupancy)

    return summarize_parking(parking_id)


@router.put("/parkings/{parking_id}")
def update_parking(parking_id: str, data: ParkingUpdate):
    base = get_parking_dir(parking_id)
    layout = read_json(base / "layout.json")

    if data.name is not None:
        layout.setdefault("parking", {})["name"] = data.name

    if data.camera is not None:
        layout["camera"] = data.camera

    write_json(base / "layout.json", layout)

    return summarize_parking(parking_id)


@router.delete("/parkings/{parking_id}", status_code=204)
def delete_parking(parking_id: str):
    base = get_parking_dir(parking_id)
    shutil.rmtree(base)


@router.get("/parkings/{parking_id}/occupancy")
def get_parking_occupancy(parking_id: str):
    return get_occupancy(parking_id)


@router.get("/parkings/{parking_id}/spots")
def get_parking_spots(parking_id: str):
    layout = get_layout(parking_id)
    occupancy = get_occupancy(parking_id)

    status_by_id = {
        item.get("spot_id"): item
        for item in occupancy.get("spots", [])
    }

    spots = []

    for spot in layout.get("spots", []):
        status = status_by_id.get(spot.get("id"), {})

        spots.append({
            **spot,
            "status": status.get("status", "unknown"),
            "confidence": status.get("confidence"),
            "vehicle": status.get("vehicle"),
        })

    return spots


@router.get("/parkings/{parking_id}/free-spots")
def get_free_spots(
    parking_id: str,
    entrance_id: str | None = Query(default=None),
):
    spots = get_parking_spots(parking_id)

    free_spots = [
        spot
        for spot in spots
        if spot.get("status") == "free"
    ]

    return {
        "parking_id": parking_id,
        "entrance_id": entrance_id,
        "spots": free_spots,
        "total": len(free_spots),
    }


@router.get("/parkings/{parking_id}/entrances")
def get_entrances(parking_id: str):
    layout = get_layout(parking_id)

    entrances = layout.get("entrances")
    if isinstance(entrances, list):
        return entrances

    return [
        {
            "id": "1",
            "name": "Въезд 1",
            "parking_id": parking_id,
        }
    ]


@router.put("/parking-spots/{spot_id}/status")
def update_spot_status(spot_id: str, data: SpotStatusUpdate):
    if data.status not in {"free", "occupied", "unknown"}:
        raise HTTPException(status_code=400, detail="Invalid status")

    DATA_ROOT.mkdir(parents=True, exist_ok=True)

    for parking_dir in DATA_ROOT.iterdir():
        if not parking_dir.is_dir():
            continue

        occupancy_file = parking_dir / "occupancy.json"
        if not occupancy_file.exists():
            continue

        occupancy = read_json(occupancy_file)
        spots = occupancy.get("spots", [])

        for spot in spots:
            if spot.get("spot_id") == spot_id:
                spot["status"] = data.status
                spot["confidence"] = None
                spot["vehicle"] = None

                summary = {
                    "total": len(spots),
                    "occupied": sum(1 for item in spots if item.get("status") == "occupied"),
                    "free": sum(1 for item in spots if item.get("status") == "free"),
                    "unknown": sum(1 for item in spots if item.get("status") == "unknown"),
                }

                occupancy["summary"] = summary
                write_json(occupancy_file, occupancy)

                return spot

    raise HTTPException(status_code=404, detail="Spot not found")