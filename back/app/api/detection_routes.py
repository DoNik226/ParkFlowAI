from pathlib import Path
import json

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/parking-map", tags=["parking-map"])

DATA_ROOT = Path("/app/data/parkings")


def safe_parking_id(parking_id: str) -> str:
    normalized = parking_id.replace("_", "").replace("-", "")

    if not normalized.isalnum():
        raise HTTPException(status_code=400, detail="Invalid parking_id")

    return parking_id


def parking_dir(parking_id: str) -> Path:
    parking_id = safe_parking_id(parking_id)
    path = DATA_ROOT / parking_id

    if not path.exists():
        raise HTTPException(status_code=404, detail="Parking not found")

    return path


def read_json(path: Path):
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path.name}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


@router.get("/{parking_id}/layout")
def get_layout(parking_id: str):
    return read_json(parking_dir(parking_id) / "layout.json")


@router.get("/{parking_id}/occupancy")
def get_occupancy(parking_id: str):
    return read_json(parking_dir(parking_id) / "occupancy.json")


@router.get("/{parking_id}/state")
def get_state(parking_id: str):
    base = parking_dir(parking_id)

    return {
        "layout": read_json(base / "layout.json"),
        "occupancy": read_json(base / "occupancy.json"),
    }