from typing import Optional, List
from sqlalchemy.orm import Session
from back.app.models.entrance import Entrance
from back.app.repositories.base_repository import BaseRepository


class EntranceRepository(BaseRepository[Entrance]):
    def __init__(self, db: Session):
        super().__init__(db, Entrance)

    def get_by_parking(self, parking_id: int, skip: int = 0, limit: int = 100) -> List[Entrance]:
        return self.db.query(Entrance).filter(Entrance.parking_id == parking_id).offset(skip).limit(limit).all()

    def get_by_name(self, parking_id: int, name: str) -> Optional[Entrance]:
        return self.db.query(Entrance).filter(
            Entrance.parking_id == parking_id,
            Entrance.name == name
        ).first()