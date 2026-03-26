from typing import Optional, List
from sqlalchemy.orm import Session
from back.app.models.road_vertex import RoadVertex
from back.app.repositories.base_repository import BaseRepository


class RoadVertexRepository(BaseRepository[RoadVertex]):
    def __init__(self, db: Session):
        super().__init__(db, RoadVertex)

    def get_by_parking(self, parking_id: int, skip: int = 0, limit: int = 100) -> List[RoadVertex]:
        return self.db.query(RoadVertex).filter(RoadVertex.parking_id == parking_id).offset(skip).limit(limit).all()

    def get_entrance_vertices(self, parking_id: int) -> List[RoadVertex]:
        return self.db.query(RoadVertex).filter(
            RoadVertex.parking_id == parking_id,
            RoadVertex.is_entrance == True
        ).all()

    def get_spot_vertices(self, parking_id: int) -> List[RoadVertex]:
        return self.db.query(RoadVertex).filter(
            RoadVertex.parking_id == parking_id,
            RoadVertex.is_spot == True
        ).all()