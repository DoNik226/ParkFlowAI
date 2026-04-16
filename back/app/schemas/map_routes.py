from typing import List, Optional, Any, Dict
from pydantic import BaseModel
from enum import Enum


class VertexType(str, Enum):
    ENTRANCE = "entrance"
    SPOT = "spot"
    REGULAR = "regular"


class RouteNodeSchema(BaseModel):
    """Схема узла маршрута"""
    vertex_id: int
    vertex_type: VertexType
    spot_number: Optional[str] = None

    class Config:
        from_attributes = True


class RouteEdgeSchema(BaseModel):
    """Схема ребра маршрута"""
    edge_id: int
    source: int
    destination: int
    length_meters: float

    class Config:
        from_attributes = True


class RouteResponseSchema(BaseModel):
    """Схема ответа с маршрутом"""
    path_nodes: List[RouteNodeSchema]
    path_edges: List[RouteEdgeSchema]
    total_distance_meters: float
    start_vertex_id: int
    end_vertex_id: int

    class Config:
        from_attributes = True


# Request schemas
class RouteFromEntranceToSpotRequest(BaseModel):
    """Запрос на построение маршрута от въезда до конкретного места"""
    parking_id: int
    entrance_vertex_id: int
    spot_vertex_id: int


class RouteFromEntranceToNearestSpotRequest(BaseModel):
    """Запрос на построение маршрута от въезда до ближайшего места"""
    parking_id: int
    entrance_vertex_id: int


class RouteFromNearestEntranceToSpotRequest(BaseModel):
    """Запрос на построение маршрута от ближайшего въезда до места"""
    parking_id: int
    spot_vertex_id: int


# Error schemas
class ErrorResponseSchema(BaseModel):
    """Схема ошибки"""
    detail: str
    status_code: int