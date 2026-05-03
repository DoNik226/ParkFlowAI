from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from back.app.database import get_db
from back.app.repositories.parking_repository import ParkingRepository
from back.app.services.map_service import MapRoutesService

router = APIRouter(prefix="", tags=["map-routes"])


class FlexibleRouteRequest(BaseModel):
    """Поддерживает старый и новый payload фронта.

    Новый вариант:
      { parking_id, entrance_vertex_id, spot_vertex_id }

    Старый/фронтовый вариант:
      { parking_id, entrance_id, spot_id }
    """

    parking_id: int | str | None = None
    parking_slug: str | None = None
    entrance_vertex_id: int | str | None = None
    spot_vertex_id: int | str | None = None
    entrance_id: int | str | None = None
    spot_id: int | str | None = None


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    text_value = str(value).strip()
    return text_value or None


def _resolve_parking(db: Session, parking_id: int | str | None, parking_slug: str | None = None):
    repo = ParkingRepository(db)
    key = parking_slug or parking_id

    if key is None:
        return None

    parking = repo.get_by_id_or_slug(str(key))
    if not parking:
        raise HTTPException(status_code=404, detail="Parking not found")

    return parking


def _parking_has_vertex(db: Session, parking_id: int, vertex_id: int) -> bool:
    row = db.execute(
        text(
            """
            SELECT 1
            FROM road_vertices
            WHERE id = :vertex_id AND parking_id = :parking_id
            LIMIT 1
            """
        ),
        {"parking_id": parking_id, "vertex_id": vertex_id},
    ).first()
    return row is not None


def _resolve_entrance_vertex_id(db: Session, parking_id: int, raw_value: Any) -> int | None:
    value = _as_str(raw_value)
    if value is None:
        return None

    # 1) Если пришёл id вершины БД.
    if value.isdigit():
        vertex_id = int(value)
        if _parking_has_vertex(db, parking_id, vertex_id):
            return vertex_id

        # 2) Если пришёл id записи entrances.
        row = db.execute(
            text(
                """
                SELECT road_vertex_id
                FROM entrances
                WHERE id = :entrance_id AND parking_id = :parking_id
                LIMIT 1
                """
            ),
            {"parking_id": parking_id, "entrance_id": vertex_id},
        ).mappings().first()
        if row and row["road_vertex_id"]:
            return int(row["road_vertex_id"])

    # 3) Если пришёл client_id вершины или client_id въезда.
    row = db.execute(
        text(
            """
            SELECT id
            FROM road_vertices
            WHERE parking_id = :parking_id AND client_id = :client_id
            LIMIT 1
            """
        ),
        {"parking_id": parking_id, "client_id": value},
    ).mappings().first()
    if row:
        return int(row["id"])

    row = db.execute(
        text(
            """
            SELECT road_vertex_id
            FROM entrances
            WHERE parking_id = :parking_id AND client_id = :client_id
            LIMIT 1
            """
        ),
        {"parking_id": parking_id, "client_id": value},
    ).mappings().first()
    if row and row["road_vertex_id"]:
        return int(row["road_vertex_id"])

    return None


def _resolve_spot_vertex_id(db: Session, parking_id: int, raw_value: Any) -> int | None:
    value = _as_str(raw_value)
    if value is None:
        return None

    # 1) Если пришёл id вершины БД.
    if value.isdigit():
        vertex_id = int(value)
        if _parking_has_vertex(db, parking_id, vertex_id):
            return vertex_id

        # 2) Если пришёл id записи parking_spots.
        row = db.execute(
            text(
                """
                SELECT road_vertex_id
                FROM parking_spots
                WHERE id = :spot_id AND parking_id = :parking_id
                LIMIT 1
                """
            ),
            {"parking_id": parking_id, "spot_id": vertex_id},
        ).mappings().first()
        if row and row["road_vertex_id"]:
            return int(row["road_vertex_id"])

    # 3) Если пришёл client_id места, номер места или client_id вершины.
    row = db.execute(
        text(
            """
            SELECT road_vertex_id
            FROM parking_spots
            WHERE parking_id = :parking_id
              AND (client_id = :value OR spot_number = :value OR label = :value)
            LIMIT 1
            """
        ),
        {"parking_id": parking_id, "value": value},
    ).mappings().first()
    if row and row["road_vertex_id"]:
        return int(row["road_vertex_id"])

    row = db.execute(
        text(
            """
            SELECT id
            FROM road_vertices
            WHERE parking_id = :parking_id AND client_id = :client_id
            LIMIT 1
            """
        ),
        {"parking_id": parking_id, "client_id": value},
    ).mappings().first()
    if row:
        return int(row["id"])

    return None


def _infer_parking_by_points(db: Session, entrance_value: Any, spot_value: Any):
    """Fallback для старого frontend API, если parking_id не передан."""
    candidates = db.execute(
        text(
            """
            SELECT id, slug, name
            FROM parkings
            WHERE COALESCE(is_active, TRUE) = TRUE
            ORDER BY id ASC
            """
        )
    ).mappings().all()

    matched = []
    for parking in candidates:
        parking_id = int(parking["id"])
        entrance_vertex_id = _resolve_entrance_vertex_id(db, parking_id, entrance_value)
        spot_vertex_id = _resolve_spot_vertex_id(db, parking_id, spot_value)
        if entrance_vertex_id and spot_vertex_id:
            matched.append((parking, entrance_vertex_id, spot_vertex_id))

    if len(matched) == 1:
        return matched[0]

    if len(matched) > 1:
        raise HTTPException(
            status_code=400,
            detail="Найдено несколько парковок для этих точек. Передайте parking_id.",
        )

    return None


def _vertex_client_map(db: Session, parking_id: int) -> dict[int, str]:
    rows = db.execute(
        text(
            """
            SELECT id, client_id
            FROM road_vertices
            WHERE parking_id = :parking_id
            """
        ),
        {"parking_id": parking_id},
    ).mappings().all()
    return {int(row["id"]): str(row["client_id"] or row["id"]) for row in rows}


def _convert_route_to_front_response(db: Session, parking, route) -> dict[str, Any]:
    client_by_db_id = _vertex_client_map(db, int(parking.id))

    path_nodes = []
    for node in route.path_nodes:
        vertex_db_id = int(node.vertex_id)
        path_nodes.append(
            {
                "vertex_id": client_by_db_id.get(vertex_db_id, str(vertex_db_id)),
                "vertex_db_id": vertex_db_id,
                "vertex_type": node.vertex_type,
                "spot_number": node.spot_number,
            }
        )

    path_edges = []
    for edge in route.path_edges:
        source_db_id = int(edge.source)
        destination_db_id = int(edge.destination)
        path_edges.append(
            {
                "edge_id": edge.edge_id,
                "source": client_by_db_id.get(source_db_id, str(source_db_id)),
                "destination": client_by_db_id.get(destination_db_id, str(destination_db_id)),
                "source_db_id": source_db_id,
                "destination_db_id": destination_db_id,
                "length_meters": edge.length_meters,
            }
        )

    return {
        "path_nodes": path_nodes,
        "path_edges": path_edges,
        "path_vertex_ids": [node["vertex_id"] for node in path_nodes],
        "path_vertex_db_ids": [node["vertex_db_id"] for node in path_nodes],
        "total_distance_meters": route.total_distance_meters,
        "start_vertex_id": client_by_db_id.get(int(route.start_vertex_id), str(route.start_vertex_id)),
        "end_vertex_id": client_by_db_id.get(int(route.end_vertex_id), str(route.end_vertex_id)),
        "start_vertex_db_id": int(route.start_vertex_id),
        "end_vertex_db_id": int(route.end_vertex_id),
        "end_spot_number": getattr(route, "end_spot_number", None),
        "parking_id": parking.slug,
        "parking_db_id": int(parking.id),
    }


def _build_route_response(db: Session, parking, entrance_value: Any, spot_value: Any) -> dict[str, Any]:
    entrance_vertex_id = _resolve_entrance_vertex_id(db, int(parking.id), entrance_value)
    spot_vertex_id = _resolve_spot_vertex_id(db, int(parking.id), spot_value)

    if not entrance_vertex_id:
        raise HTTPException(status_code=404, detail="Точка въезда не найдена в графе парковки")

    if not spot_vertex_id:
        raise HTTPException(status_code=404, detail="Парковочное место не связано с вершиной графа")

    route = MapRoutesService(db).build_route_from_entrance_to_spot(
        int(parking.id),
        entrance_vertex_id,
        spot_vertex_id,
    )

    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Для данной точки маршрут не найден. Проверьте, что между въездом и местом есть связанные ребра графа.",
        )

    return _convert_route_to_front_response(db, parking, route)


@router.post(
    "/routes",
    summary="Построить маршрут от въезда до конкретного места",
    description="Поддерживает id из БД и client-id, которые использует фронтовый редактор карты.",
)
def post_route_from_entrance_to_spot(
    request: FlexibleRouteRequest,
    db: Session = Depends(get_db),
):
    entrance_value = request.entrance_vertex_id or request.entrance_id
    spot_value = request.spot_vertex_id or request.spot_id

    if entrance_value is None or spot_value is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нужно передать entrance_vertex_id/entrance_id и spot_vertex_id/spot_id",
        )

    parking = _resolve_parking(db, request.parking_id, request.parking_slug)

    if parking is None:
        inferred = _infer_parking_by_points(db, entrance_value, spot_value)
        if inferred is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="parking_id не передан, и парковку не удалось определить по точкам маршрута",
            )
        parking, entrance_vertex_id, spot_vertex_id = inferred
        route = MapRoutesService(db).build_route_from_entrance_to_spot(
            int(parking["id"]),
            entrance_vertex_id,
            spot_vertex_id,
        )
        if not route:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Для данной точки маршрут не найден. Проверьте граф.",
            )

        class ParkingLike:
            id = int(parking["id"])
            slug = parking["slug"]

        return _convert_route_to_front_response(db, ParkingLike, route)

    return _build_route_response(db, parking, entrance_value, spot_value)


@router.get(
    "/parkings/{parking_id}/nearest",
    summary="Построить маршрут от въезда до ближайшего свободного места",
)
def get_route_from_entrance_to_nearest_spot_by_parking(
    parking_id: str,
    entrance_id: str | None = Query(default=None),
    entrance_vertex_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    parking = _resolve_parking(db, parking_id)
    entrance_value = entrance_vertex_id or entrance_id

    entrance_db_id = _resolve_entrance_vertex_id(db, int(parking.id), entrance_value)
    if not entrance_db_id:
        raise HTTPException(status_code=404, detail="Точка въезда не найдена в графе парковки")

    route = MapRoutesService(db).build_route_from_entrance_to_nearest_spot(int(parking.id), entrance_db_id)
    if not route:
        raise HTTPException(status_code=404, detail="Свободные места не найдены или маршрут недоступен")

    return _convert_route_to_front_response(db, parking, route)


@router.get(
    "/parkings/nearest",
    summary="Старый endpoint: маршрут от въезда до ближайшего свободного места",
)
def get_route_from_entrance_to_nearest_spot_legacy(
    parking_id: int | str = Query(..., description="ID или slug парковки"),
    entrance_vertex_id: str | None = Query(default=None),
    entrance_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    parking = _resolve_parking(db, parking_id)
    entrance_value = entrance_vertex_id or entrance_id

    entrance_db_id = _resolve_entrance_vertex_id(db, int(parking.id), entrance_value)
    if not entrance_db_id:
        raise HTTPException(status_code=404, detail="Точка въезда не найдена в графе парковки")

    route = MapRoutesService(db).build_route_from_entrance_to_nearest_spot(int(parking.id), entrance_db_id)
    if not route:
        raise HTTPException(status_code=404, detail="Свободные места не найдены или маршрут недоступен")

    return _convert_route_to_front_response(db, parking, route)
