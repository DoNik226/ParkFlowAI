from typing import Optional, List
from sqlalchemy.orm import Session
from back.app.models.parking import Parking
from back.app.repositories.base_repository import BaseRepository


class ParkingRepository(BaseRepository[Parking]):
    def __init__(self, db: Session):
        super().__init__(db, Parking)

    def get_active_parkings(self, skip: int = 0, limit: int = 100) -> List[Parking]:
        return self.db.query(Parking).filter(Parking.is_active == True).offset(skip).limit(limit).all()

    def get_by_name(self, name: str) -> Optional[Parking]:
        return self.db.query(Parking).filter(Parking.name == name).first()

    def get_with_stats(self, parking_id: int) -> Optional[Parking]:
        return self.db.query(Parking).filter(Parking.id == parking_id).first()