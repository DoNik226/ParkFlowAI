from typing import Optional, List
from sqlalchemy.orm import Session

from back.app.models import RoadVertex
from back.app.models.road_edge import RoadEdge
from back.app.repositories.base_repository import BaseRepository


class RoadEdgeRepository(BaseRepository[RoadEdge]):
    def __init__(self, db: Session):
        super().__init__(db, RoadEdge)

    def get_by_vertices(self, source_id: int, destination_id: int) -> Optional[RoadEdge]:
        return self.db.query(RoadEdge).filter(
            RoadEdge.source == source_id,
            RoadEdge.destination == destination_id
        ).first()

    def get_outgoing_edges(self, vertex_id: int) -> List[RoadEdge]:
        return self.db.query(RoadEdge).filter(RoadEdge.source == vertex_id).all()

    def get_incoming_edges(self, vertex_id: int) -> List[RoadEdge]:
        return self.db.query(RoadEdge).filter(RoadEdge.destination == vertex_id).all()

    def get_graph_for_parking(self, parking_id: int) -> List[RoadEdge]:
        return self.db.query(RoadEdge).join(
            RoadVertex, RoadEdge.source == RoadVertex.id
        ).filter(RoadVertex.parking_id == parking_id).all()