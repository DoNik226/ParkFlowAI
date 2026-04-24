from fastapi import APIRouter

from back.app.api.stub_utils import not_implemented_response
from back.app.schemas.stubs import (
    EntranceResponse,
    FreeSpotResponse,
    MessageResponse,
    NearestParkingResponse,
    ParkingDetailResponse,
    ParkingListItem,
    ParkingOccupancyResponse,
    ParkingSpotResponse,
    ParkingSpotStatusUpdateRequest,
    ParkingUpsertRequest,
)

router = APIRouter(tags=["parkings"])


@router.get("/parkings", response_model=list[ParkingListItem])
async def list_parkings():
    return not_implemented_response("GET", "/parkings", "List parking lots with occupancy summary")


@router.get("/parkings/{parking_id}", response_model=ParkingDetailResponse)
async def get_parking(parking_id: int):
    return not_implemented_response("GET", f"/parkings/{parking_id}", "Get parking lot details")


@router.post("/parkings", response_model=MessageResponse)
async def create_parking(data: ParkingUpsertRequest):
    return not_implemented_response("POST", "/parkings", "Create a parking lot")


@router.put("/parkings/{parking_id}", response_model=MessageResponse)
async def update_parking(parking_id: int, data: ParkingUpsertRequest):
    return not_implemented_response("PUT", f"/parkings/{parking_id}", "Update a parking lot")


@router.delete("/parkings/{parking_id}", response_model=MessageResponse)
async def delete_parking(parking_id: int):
    return not_implemented_response("DELETE", f"/parkings/{parking_id}", "Delete a parking lot")


@router.get("/parkings/{parking_id}/occupancy", response_model=ParkingOccupancyResponse)
async def get_parking_occupancy(parking_id: int):
    return not_implemented_response(
        "GET",
        f"/parkings/{parking_id}/occupancy",
        "Get occupancy cache for a parking lot",
    )


@router.get("/parkings/{parking_id}/spots", response_model=list[ParkingSpotResponse])
async def list_parking_spots(parking_id: int):
    return not_implemented_response(
        "GET",
        f"/parkings/{parking_id}/spots",
        "List parking spots for a parking lot",
    )


@router.get("/parkings/{parking_id}/free-spots", response_model=list[FreeSpotResponse])
async def list_free_spots(parking_id: int, entrance_id: int):
    return not_implemented_response(
        "GET",
        f"/parkings/{parking_id}/free-spots",
        "List free parking spots with distance from the selected entrance",
    )


@router.put("/parking-spots/{spot_id}/status", response_model=MessageResponse)
async def update_spot_status(spot_id: int, data: ParkingSpotStatusUpdateRequest):
    return not_implemented_response(
        "PUT",
        f"/parking-spots/{spot_id}/status",
        "Update a parking spot status",
    )


@router.get("/parkings/{parking_id}/entrances", response_model=list[EntranceResponse])
async def list_parking_entrances(parking_id: int):
    return not_implemented_response(
        "GET",
        f"/parkings/{parking_id}/entrances",
        "List parking entrances",
    )


@router.get("/parkings/{parking_id}/nearest", response_model=NearestParkingResponse)
async def get_nearest_parking(parking_id: int, entrance_id: int):
    return not_implemented_response(
        "GET",
        f"/parkings/{parking_id}/nearest",
        "Find the nearest available parking recommendation",
    )
