from pathlib import Path
import json

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/parking-map", tags=["parking-map"])

DATA_ROOT = Path("/app/data/parkings")


def safe_parking_dir(parking_id: str) -> Path:
    normalized = parking_id.replace("_", "").replace("-", "")

    if not normalized.isalnum():
        raise HTTPException(status_code=400, detail="Invalid parking_id")

    parking_dir = DATA_ROOT / parking_id

    if not parking_dir.exists():
        raise HTTPException(status_code=404, detail="Parking not found")

    return parking_dir


def read_json(path: Path):
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path.name}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


@router.get("/{parking_id}/layout")
def get_layout(parking_id: str):
    parking_dir = safe_parking_dir(parking_id)
    return read_json(parking_dir / "layout.json")


@router.get("/{parking_id}/occupancy")
def get_occupancy(parking_id: str):
    parking_dir = safe_parking_dir(parking_id)
    return read_json(parking_dir / "occupancy.json")


@router.get("/{parking_id}/state")
def get_state(parking_id: str):
    parking_dir = safe_parking_dir(parking_id)

    return {
        "layout": read_json(parking_dir / "layout.json"),
        "occupancy": read_json(parking_dir / "occupancy.json"),
    }