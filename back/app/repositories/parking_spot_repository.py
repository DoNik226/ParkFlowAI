from typing import Optional, List
from sqlalchemy.orm import Session
from back.app.models.parking_spot import ParkingSpot
from back.app.repositories.base_repository import BaseRepository
from back.app.models.enums import SpotStatus


class ParkingSpotRepository(BaseRepository[ParkingSpot]):
    def __init__(self, db: Session):
        super().__init__(db, ParkingSpot)

    def get_by_parking(self, parking_id: int, skip: int = 0, limit: int = 100) -> List[ParkingSpot]:
        return self.db.query(ParkingSpot).filter(ParkingSpot.parking_id == parking_id).offset(skip).limit(limit).all()

    def get_free_spots(self, parking_id: int) -> List[ParkingSpot]:
        return self.db.query(ParkingSpot).filter(
            ParkingSpot.parking_id == parking_id,
            ParkingSpot.status == SpotStatus.FREE.value
        ).all()

    def get_occupied_spots(self, parking_id: int) -> List[ParkingSpot]:
        return self.db.query(ParkingSpot).filter(
            ParkingSpot.parking_id == parking_id,
            ParkingSpot.status == SpotStatus.OCCUPIED.value
        ).all()

    def update_spot_status(self, spot_id: int, status: SpotStatus) -> Optional[ParkingSpot]:
        return self.update(spot_id, status=status.value)

    def get_by_spot_number(self, parking_id: int, spot_number: str) -> Optional[ParkingSpot]:
        return self.db.query(ParkingSpot).filter(
            ParkingSpot.parking_id == parking_id,
            ParkingSpot.spot_number == spot_number
        ).first()

    def get_statistics(self, parking_id: int) -> dict:
        total = self.db.query(ParkingSpot).filter(ParkingSpot.parking_id == parking_id).count()
        free = self.db.query(ParkingSpot).filter(
            ParkingSpot.parking_id == parking_id,
            ParkingSpot.status == SpotStatus.FREE.value
        ).count()
        occupied = total - free

        return {
            "total": total,
            "free": free,
            "occupied": occupied,
            "occupancy_percentage": (occupied / total * 100) if total > 0 else 0
        }