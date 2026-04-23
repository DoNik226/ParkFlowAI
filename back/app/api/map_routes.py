from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from back.app.database import get_db
from back.app.services.map_service import MapRoutesService
from back.app.schemas.map_routes import (
    RouteResponseSchema,
    RouteFromEntranceToSpotRequest,
    ErrorResponseSchema,
    RouteNodeSchema,
    RouteEdgeSchema
)

router = APIRouter(prefix="", tags=["map-routes"])


def convert_to_response_schema(route):
    """Конвертирует RouteResponse в RouteResponseSchema"""
    return RouteResponseSchema(
        path_nodes=[
            RouteNodeSchema(
                vertex_id=node.vertex_id,
                vertex_type=node.vertex_type,
                spot_number=node.spot_number
            ) for node in route.path_nodes
        ],
        path_edges=[
            RouteEdgeSchema(
                edge_id=edge.edge_id,
                source=edge.source,
                destination=edge.destination,
                length_meters=edge.length_meters
            ) for edge in route.path_edges
        ],
        total_distance_meters=route.total_distance_meters,
        start_vertex_id=route.start_vertex_id,
        end_vertex_id=route.end_vertex_id
    )


@router.post(
    "/routes",
    response_model=RouteResponseSchema,
    responses={
        404: {"model": ErrorResponseSchema, "description": "Маршрут не найден"},
        400: {"model": ErrorResponseSchema, "description": "Некорректные параметры"}
    },
    summary="Построить маршрут от въезда до конкретного места",
    description="Строит оптимальный маршрут от указанного въезда до конкретного парковочного места"
)
def post_route_from_entrance_to_spot(
        request: RouteFromEntranceToSpotRequest,
        db: Session = Depends(get_db)
):
    """
    POST: Построить маршрут от конкретного въезда до конкретного места

    - **parking_id**: ID парковки
    - **entrance_vertex_id**: ID вершины въезда
    - **spot_vertex_id**: ID вершины парковочного места
    """
    # Валидация параметров
    if request.parking_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректный ID парковки"
        )

    if request.entrance_vertex_id <= 0 or request.spot_vertex_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректные ID вершин"
        )

    service = MapRoutesService(db)
    route = service.build_route_from_entrance_to_spot(
        request.parking_id,
        request.entrance_vertex_id,
        request.spot_vertex_id
    )

    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Маршрут не найден или вершины недостижимы"
        )

    return convert_to_response_schema(route)


@router.get(
    "/parkings/nearest",
    response_model=RouteResponseSchema,
    responses={
        404: {"model": ErrorResponseSchema, "description": "Свободные места не найдены"},
        400: {"model": ErrorResponseSchema, "description": "Некорректные параметры"}
    },
    summary="Построить маршрут от въезда до ближайшего свободного места",
    description="Строит оптимальный маршрут от указанного въезда до ближайшего свободного парковочного места"
)
def get_route_from_entrance_to_nearest_spot(
        parking_id: int = Query(..., description="ID парковки", gt=0),
        entrance_vertex_id: int = Query(..., description="ID вершины въезда", gt=0),
        db: Session = Depends(get_db)
):
    """
    GET: Построить маршрут от въезда до ближайшего свободного места

    Параметры запроса:
    - **parking_id**: ID парковки
    - **entrance_vertex_id**: ID вершины въезда
    """
    service = MapRoutesService(db)
    route = service.build_route_from_entrance_to_nearest_spot(
        parking_id,
        entrance_vertex_id
    )

    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Свободные места не найдены или маршрут недоступен"
        )

    return convert_to_response_schema(route)

