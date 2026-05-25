from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from back.app.models.parking import Parking


VALID_SPOT_STATUSES = {"free", "occupied", "unknown"}


def _json(value: Any, default: Any = None) -> str:
    if value is None:
        value = default
    return json.dumps(value, ensure_ascii=False)


def _loads(value: Any, default: Any = None) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return default


def _get(obj: dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in obj and obj[name] is not None:
            return obj[name]
    return default


def _as_client_id(value: Any, fallback: str) -> str:
    if value is None or value == "":
        return fallback
    return str(value)


def _status(value: Any) -> str:
    value = str(value or "free")
    return value if value in VALID_SPOT_STATUSES else "free"


def _point_from_item(item: dict[str, Any]) -> tuple[float | None, float | None]:
    point = _get(item, "point", "position", "center", default={}) or {}
    x = _get(item, "x", default=point.get("x"))
    y = _get(item, "y", default=point.get("y"))

    try:
        x = None if x is None else float(x)
    except (TypeError, ValueError):
        x = None

    try:
        y = None if y is None else float(y)
    except (TypeError, ValueError):
        y = None

    return x, y


def _center_from_polygon(polygon: list[dict[str, Any]]) -> tuple[float | None, float | None]:
    if not polygon:
        return None, None

    points: list[tuple[float, float]] = []
    for point in polygon:
        try:
            points.append((float(point.get("x", 0)), float(point.get("y", 0))))
        except (TypeError, ValueError, AttributeError):
            continue

    if not points:
        return None, None

    return (
        sum(point[0] for point in points) / len(points),
        sum(point[1] for point in points) / len(points),
    )


class ParkingLayoutStorageService:
    """Хранит layout/occupancy в таблицах и собирает прежний JSON-формат для фронта/детектора.

    Важно: JSON-файлы layout и occupancy после этого сервиса являются только runtime-кэшем.
    Источник истины — таблицы PostgreSQL.
    """

    def __init__(self, db: Session):
        self.db = db

    def save_layout_to_db(self, parking: Parking, layout: dict[str, Any]) -> None:
        parking_id = int(parking.id)

        self.db.execute(text("DELETE FROM road_edges WHERE parking_id = :parking_id"), {"parking_id": parking_id})
        self.db.execute(text("DELETE FROM entrances WHERE parking_id = :parking_id"), {"parking_id": parking_id})
        self.db.execute(text("DELETE FROM parking_spots WHERE parking_id = :parking_id"), {"parking_id": parking_id})
        self.db.execute(text("DELETE FROM road_vertices WHERE parking_id = :parking_id"), {"parking_id": parking_id})

        self.db.execute(
            text(
                """
                UPDATE parkings
                SET layout_meta = CAST(:layout_meta AS jsonb),
                    layout_zones = CAST(:layout_zones AS jsonb),
                    layout_calibration = CAST(:layout_calibration AS jsonb),
                    layout_version = COALESCE(layout_version, 0) + 1,
                    updated_at = NOW()
                WHERE id = :parking_id
                """
            ),
            {
                "parking_id": parking_id,
                "layout_meta": _json(
                    {
                        "parking": layout.get("parking", {}),
                        "camera": layout.get("camera", {}),
                        "frame_meta": layout.get("frame_meta") or layout.get("frame") or {},
                        "source_type": layout.get("source_type"),
                        "source_path": layout.get("source_path"),
                    },
                    {},
                ),
                "layout_zones": _json(layout.get("zones", []), []),
                "layout_calibration": _json(layout.get("calibration"), None),
            },
        )

        client_to_vertex_id: dict[str, int] = {}

        def add_vertex(vertex_payload: dict[str, Any], *, fallback_id: str, is_spot: bool, is_entrance: bool) -> int:
            client_id = _as_client_id(_get(vertex_payload, "id", "client_id", "vertex_id"), fallback_id)
            if client_id in client_to_vertex_id:
                return client_to_vertex_id[client_id]

            x, y = _point_from_item(vertex_payload)
            row = self.db.execute(
                text(
                    """
                    INSERT INTO road_vertices
                        (parking_id, client_id, x, y, label, is_spot, is_entrance, payload)
                    VALUES
                        (:parking_id, :client_id, :x, :y, :label, :is_spot, :is_entrance, CAST(:payload AS jsonb))
                    RETURNING id
                    """
                ),
                {
                    "parking_id": parking_id,
                    "client_id": client_id,
                    "x": x,
                    "y": y,
                    "label": _get(vertex_payload, "label", "name"),
                    "is_spot": is_spot,
                    "is_entrance": is_entrance,
                    "payload": _json(vertex_payload, {}),
                },
            ).first()

            vertex_id = int(row[0])
            client_to_vertex_id[client_id] = vertex_id
            return vertex_id

        for index, vertex in enumerate(layout.get("vertices") or layout.get("road_vertices") or [], start=1):
            if not isinstance(vertex, dict):
                continue
            add_vertex(
                vertex,
                fallback_id=f"vertex_{index}",
                is_spot=bool(vertex.get("is_spot", False)),
                is_entrance=bool(vertex.get("is_entrance", False)),
            )

        for index, spot in enumerate(layout.get("spots") or [], start=1):
            if not isinstance(spot, dict):
                continue

            client_id = _as_client_id(_get(spot, "id", "spot_id", "client_id"), f"spot_{index}")
            polygon = _get(spot, "polygon", "corners", default=[]) or []
            x, y = _point_from_item(spot)
            if x is None or y is None:
                x, y = _center_from_polygon(polygon)

            vertex_client_id = _as_client_id(
                _get(spot, "road_vertex_client_id", "road_vertex_id", "vertex_id"),
                f"vertex_for_{client_id}",
            )
            vertex_payload = {
                "id": vertex_client_id,
                "x": x,
                "y": y,
                "label": _get(spot, "label", "number", "spot_number", default=client_id),
                "source": "spot",
                "spot_id": client_id,
            }
            vertex_id = add_vertex(vertex_payload, fallback_id=vertex_client_id, is_spot=True, is_entrance=False)

            # Алиасы нужны для графа: редактор может соединять ребра как с vertex_for_spot_1,
            # так и напрямую со spot_1/номером места.
            client_to_vertex_id[client_id] = vertex_id
            spot_number_alias = str(_get(spot, "number", "spot_number", "label", default=client_id))
            client_to_vertex_id[spot_number_alias] = vertex_id

            self.db.execute(
                text(
                    """
                    INSERT INTO parking_spots
                        (parking_id, client_id, label, spot_number, status, road_vertex_id,
                         row_index, col_index, zone, zone_id, polygon, enabled, payload)
                    VALUES
                        (:parking_id, :client_id, :label, :spot_number, CAST(:status AS SpotStatus), :road_vertex_id,
                         :row_index, :col_index, :zone, :zone_id, CAST(:polygon AS jsonb), :enabled, CAST(:payload AS jsonb))
                    """
                ),
                {
                    "parking_id": parking_id,
                    "client_id": client_id,
                    "label": _get(spot, "label", "number", "spot_number", default=client_id),
                    "spot_number": str(_get(spot, "number", "spot_number", "label", default=client_id)),
                    "status": _status(spot.get("status")),
                    "road_vertex_id": vertex_id,
                    "row_index": spot.get("row"),
                    "col_index": spot.get("col"),
                    "zone": None if spot.get("zone") is None else str(spot.get("zone")),
                    "zone_id": spot.get("zone_id"),
                    "polygon": _json(polygon, []),
                    "enabled": bool(spot.get("enabled", True)),
                    "payload": _json(spot, {}),
                },
            )

        for index, entrance in enumerate(layout.get("entrances") or [], start=1):
            if not isinstance(entrance, dict):
                continue

            client_id = _as_client_id(_get(entrance, "id", "client_id"), f"entrance_{index}")
            x, y = _point_from_item(entrance)
            vertex_client_id = _as_client_id(
                _get(entrance, "road_vertex_client_id", "road_vertex_id", "vertex_id"),
                f"vertex_for_{client_id}",
            )
            vertex_id = add_vertex(
                {
                    "id": vertex_client_id,
                    "x": x,
                    "y": y,
                    "label": _get(entrance, "name", "label", default=f"Въезд {index}"),
                    "source": "entrance",
                    "entrance_id": client_id,
                },
                fallback_id=vertex_client_id,
                is_spot=False,
                is_entrance=True,
            )

            self.db.execute(
                text(
                    """
                    INSERT INTO entrances
                        (parking_id, client_id, name, road_vertex_id, x, y, payload)
                    VALUES
                        (:parking_id, :client_id, :name, :road_vertex_id, :x, :y, CAST(:payload AS jsonb))
                    """
                ),
                {
                    "parking_id": parking_id,
                    "client_id": client_id,
                    "name": str(_get(entrance, "name", "label", default=f"Въезд {index}")),
                    "road_vertex_id": vertex_id,
                    "x": x,
                    "y": y,
                    "payload": _json(entrance, {}),
                },
            )

        for index, edge in enumerate(layout.get("edges") or layout.get("road_edges") or layout.get("roads") or [], start=1):
            if not isinstance(edge, dict):
                continue

            source_client = str(_get(edge, "source", "from", "source_id", "from_id", default=""))
            destination_client = str(_get(edge, "destination", "to", "destination_id", "to_id", default=""))
            source_id = client_to_vertex_id.get(source_client)
            destination_id = client_to_vertex_id.get(destination_client)

            if not source_id or not destination_id or source_id == destination_id:
                continue

            length_meters = edge.get("length_meters") or edge.get("length") or edge.get("distance") or 1.0
            try:
                length_meters = max(float(length_meters), 0.01)
            except (TypeError, ValueError):
                length_meters = 1.0

            self.db.execute(
                text(
                    """
                    INSERT INTO road_edges
                        (parking_id, client_id, source, destination, length_meters, one_way, is_bidirectional, payload)
                    VALUES
                        (:parking_id, :client_id, :source, :destination, :length_meters,
                         :one_way, :is_bidirectional, CAST(:payload AS jsonb))
                    """
                ),
                {
                    "parking_id": parking_id,
                    "client_id": _as_client_id(_get(edge, "id", "client_id"), f"edge_{index}"),
                    "source": source_id,
                    "destination": destination_id,
                    "length_meters": length_meters,
                    "one_way": bool(edge.get("one_way", False)),
                    "is_bidirectional": bool(edge.get("is_bidirectional", not edge.get("one_way", False))),
                    "payload": _json(edge, {}),
                },
            )

        self.db.commit()

    def build_layout_from_db(self, parking: Parking) -> dict[str, Any]:
        parking_id = int(parking.id)

        parking_row = self.db.execute(
            text(
                """
                SELECT id, name, slug, layout_meta, layout_zones, layout_calibration
                FROM parkings
                WHERE id = :parking_id
                """
            ),
            {"parking_id": parking_id},
        ).mappings().first()

        camera = self.db.execute(
            text(
                """
                SELECT id, name, source_type, source_url, test_video_path
                FROM cameras
                WHERE parking_id = :parking_id
                ORDER BY id ASC
                LIMIT 1
                """
            ),
            {"parking_id": parking_id},
        ).mappings().first()

        vertices = self.db.execute(
            text(
                """
                SELECT id, client_id, x, y, label, is_spot, is_entrance, payload
                FROM road_vertices
                WHERE parking_id = :parking_id
                ORDER BY id ASC
                """
            ),
            {"parking_id": parking_id},
        ).mappings().all()
        vertex_by_id = {row["id"]: row for row in vertices}

        spots = self.db.execute(
            text(
                """
                SELECT id, parking_id, client_id, label, spot_number, status::text AS status, road_vertex_id,
                       row_index, col_index, zone, zone_id, polygon, enabled, confidence, vehicle, payload
                FROM parking_spots
                WHERE parking_id = :parking_id
                ORDER BY id ASC
                """
            ),
            {"parking_id": parking_id},
        ).mappings().all()

        edges = self.db.execute(
            text(
                """
                SELECT id, client_id, source, destination, length_meters, one_way, is_bidirectional, payload
                FROM road_edges
                WHERE parking_id = :parking_id
                ORDER BY id ASC
                """
            ),
            {"parking_id": parking_id},
        ).mappings().all()

        entrances = self.db.execute(
            text(
                """
                SELECT id, client_id, name, road_vertex_id, x, y, payload
                FROM entrances
                WHERE parking_id = :parking_id
                ORDER BY id ASC
                """
            ),
            {"parking_id": parking_id},
        ).mappings().all()

        layout_spots = []
        for spot in spots:
            payload = dict(_loads(spot["payload"], {}) or {})
            polygon = _loads(spot["polygon"], []) or payload.get("polygon") or payload.get("corners") or []
            client_id = spot["client_id"] or str(spot["id"])
            payload.update(
                {
                    "id": client_id,
                    "spot_id": client_id,
                    "number": spot["spot_number"],
                    "label": spot["label"] or spot["spot_number"],
                    "status": spot["status"],
                    "enabled": spot["enabled"],
                    "row": spot["row_index"],
                    "col": spot["col_index"],
                    "zone": spot["zone"],
                    "zone_id": spot["zone_id"],
                    "polygon": polygon,
                    "corners": payload.get("corners", polygon),
                    "road_vertex_id": spot["road_vertex_id"],
                }
            )
            layout_spots.append(payload)

        layout_vertices = []
        for vertex in vertices:
            payload = dict(_loads(vertex["payload"], {}) or {})
            payload.update(
                {
                    "id": vertex["client_id"] or str(vertex["id"]),
                    "db_id": vertex["id"],
                    "x": vertex["x"],
                    "y": vertex["y"],
                    "label": vertex["label"],
                    "type": payload.get("type") or ("entrance" if vertex["is_entrance"] else "spot_access" if vertex["is_spot"] else "regular"),
                    "is_spot": vertex["is_spot"],
                    "is_entrance": vertex["is_entrance"],
                }
            )
            layout_vertices.append(payload)

        layout_edges = []
        for edge in edges:
            payload = dict(_loads(edge["payload"], {}) or {})
            source_vertex = vertex_by_id.get(edge["source"])
            destination_vertex = vertex_by_id.get(edge["destination"])
            source_client = source_vertex["client_id"] if source_vertex else edge["source"]
            destination_client = destination_vertex["client_id"] if destination_vertex else edge["destination"]
            payload.update(
                {
                    "id": edge["client_id"] or str(edge["id"]),
                    "source": source_client,
                    "destination": destination_client,
                    "length_meters": edge["length_meters"],
                    "one_way": edge["one_way"],
                    "is_bidirectional": edge["is_bidirectional"],
                }
            )
            layout_edges.append(payload)

        layout_entrances = []
        for entrance in entrances:
            payload = dict(_loads(entrance["payload"], {}) or {})
            payload.update(
                {
                    "id": entrance["client_id"] or str(entrance["id"]),
                    "name": entrance["name"],
                    "road_vertex_id": (vertex_by_id.get(entrance["road_vertex_id"] or 0) or {}).get("client_id") or entrance["road_vertex_id"],
                    "road_vertex_db_id": entrance["road_vertex_id"],
                    "x": entrance["x"],
                    "y": entrance["y"],
                }
            )
            layout_entrances.append(payload)

        meta = _loads(parking_row["layout_meta"], {}) if parking_row else {}
        zones = _loads(parking_row["layout_zones"], []) if parking_row else []
        calibration = _loads(parking_row["layout_calibration"], None) if parking_row else None

        parking_payload = dict(meta.get("parking") or {})
        parking_payload.update(
            {
                "id": str(getattr(parking, "slug", None) or parking_id),
                "db_id": parking_id,
                "name": getattr(parking, "name", None) or (parking_row["name"] if parking_row else None),
            }
        )

        camera_payload = dict(meta.get("camera") or {})
        if camera:
            camera_payload.update(
                {
                    "id": camera["id"],
                    "name": camera["name"],
                    "source_type": camera["source_type"],
                    "source_url": camera["source_url"],
                    "test_video_path": camera["test_video_path"],
                }
            )
        elif "id" not in camera_payload:
            camera_payload["id"] = "default_camera"

        frame_meta = meta.get("frame_meta") or meta.get("frame") or {}

        layout = {
            "parking": parking_payload,
            "camera": camera_payload,
            "frame_meta": frame_meta,
            "calibration": calibration,
            "zones": zones or [],
            "spots": layout_spots,
            "vertices": layout_vertices,
            "road_vertices": layout_vertices,
            "edges": layout_edges,
            "road_edges": layout_edges,
            "entrances": layout_entrances,
        }

        if meta.get("source_type") is not None:
            layout["source_type"] = meta.get("source_type")
        if meta.get("source_path") is not None:
            layout["source_path"] = meta.get("source_path")

        return layout

    def save_occupancy_to_db(self, parking_id: int, occupancy: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc)
        parking_id = int(parking_id)

        occupancy_by_spot_id = {
            str(item.get("spot_id")): item
            for item in occupancy.get("spots", [])
            if isinstance(item, dict) and item.get("spot_id") is not None
        }

        spots = self.db.execute(
            text(
                """
                SELECT id, client_id, spot_number
                FROM parking_spots
                WHERE parking_id = :parking_id
                """
            ),
            {"parking_id": parking_id},
        ).mappings().all()

        for spot in spots:
            item = (
                occupancy_by_spot_id.get(str(spot["client_id"]))
                or occupancy_by_spot_id.get(str(spot["spot_number"]))
                or occupancy_by_spot_id.get(str(spot["id"]))
            )
            if not item:
                continue

            self.db.execute(
                text(
                    """
                    UPDATE parking_spots
                    SET status = CAST(:status AS SpotStatus),
                        confidence = :confidence,
                        vehicle = CAST(:vehicle AS jsonb),
                        last_status_at = :last_status_at
                    WHERE id = :spot_db_id
                    """
                ),
                {
                    "spot_db_id": spot["id"],
                    "status": _status(item.get("status")),
                    "confidence": item.get("confidence"),
                    "vehicle": _json(item.get("vehicle"), None),
                    "last_status_at": now,
                },
            )

        summary = occupancy.get("summary", {}) or {}
        total = int(summary.get("total") or len(occupancy_by_spot_id) or 0)
        free = int(summary.get("free") or 0)
        occupied = int(summary.get("occupied") or 0)
        unknown = int(summary.get("unknown") or max(total - free - occupied, 0))
        occupancy_percentage = (occupied / total * 100) if total else 0
        camera_id = occupancy.get("camera_id") if isinstance(occupancy.get("camera_id"), int) else None

        self.db.execute(
            text(
                """
                INSERT INTO parking_occupancy_cache
                    (parking_id, total_spots, free_spots, occupied_spots, unknown_spots,
                     occupancy_percentage, last_calculated, frame_index, timestamp_sec,
                     params, source_type, source_path, camera_id)
                VALUES
                    (:parking_id, :total_spots, :free_spots, :occupied_spots, :unknown_spots,
                     :occupancy_percentage, :last_calculated, :frame_index, :timestamp_sec,
                     CAST(:params AS jsonb), :source_type, :source_path, :camera_id)
                ON CONFLICT (parking_id) DO UPDATE SET
                    total_spots = EXCLUDED.total_spots,
                    free_spots = EXCLUDED.free_spots,
                    occupied_spots = EXCLUDED.occupied_spots,
                    unknown_spots = EXCLUDED.unknown_spots,
                    occupancy_percentage = EXCLUDED.occupancy_percentage,
                    last_calculated = EXCLUDED.last_calculated,
                    frame_index = EXCLUDED.frame_index,
                    timestamp_sec = EXCLUDED.timestamp_sec,
                    params = EXCLUDED.params,
                    source_type = EXCLUDED.source_type,
                    source_path = EXCLUDED.source_path,
                    camera_id = EXCLUDED.camera_id
                """
            ),
            {
                "parking_id": parking_id,
                "total_spots": total,
                "free_spots": free,
                "occupied_spots": occupied,
                "unknown_spots": unknown,
                "occupancy_percentage": occupancy_percentage,
                "last_calculated": now,
                "frame_index": occupancy.get("frame_index"),
                "timestamp_sec": occupancy.get("timestamp_sec"),
                "params": _json(occupancy.get("params", {}), {}),
                "source_type": occupancy.get("source_type"),
                "source_path": occupancy.get("source_path"),
                "camera_id": camera_id,
            },
        )

        self.db.commit()

    def build_occupancy_from_db(self, parking: Parking) -> dict[str, Any]:
        parking_id = int(parking.id)

        camera = self.db.execute(
            text(
                """
                SELECT id
                FROM cameras
                WHERE parking_id = :parking_id
                ORDER BY id ASC
                LIMIT 1
                """
            ),
            {"parking_id": parking_id},
        ).mappings().first()

        cache = self.db.execute(
            text(
                """
                SELECT frame_index, timestamp_sec, params, source_type, source_path, camera_id
                FROM parking_occupancy_cache
                WHERE parking_id = :parking_id
                """
            ),
            {"parking_id": parking_id},
        ).mappings().first()

        spots = self.db.execute(
            text(
                """
                SELECT id, client_id, spot_number, status::text AS status, enabled, confidence,
                       row_index, col_index, zone, zone_id, vehicle
                FROM parking_spots
                WHERE parking_id = :parking_id
                ORDER BY id ASC
                """
            ),
            {"parking_id": parking_id},
        ).mappings().all()

        occupied = sum(1 for spot in spots if spot["status"] == "occupied")
        free = sum(1 for spot in spots if spot["status"] == "free")
        unknown = len(spots) - occupied - free

        return {
            "parking_id": str(getattr(parking, "slug", None) or parking_id),
            "parking_name": parking.name,
            "camera_id": (cache["camera_id"] if cache and cache["camera_id"] else None) or (camera["id"] if camera else "default_camera"),
            "frame_index": cache["frame_index"] if cache else 0,
            "timestamp_sec": cache["timestamp_sec"] if cache else 0.0,
            "summary": {
                "total": len(spots),
                "occupied": occupied,
                "free": free,
                "unknown": unknown,
            },
            "params": _loads(cache["params"], {}) if cache else {},
            "spots": [
                {
                    "spot_id": spot["client_id"] or str(spot["id"]),
                    "status": spot["status"],
                    "enabled": spot["enabled"],
                    "confidence": spot["confidence"],
                    "row": spot["row_index"],
                    "col": spot["col_index"],
                    "zone": spot["zone"],
                    "zone_id": spot["zone_id"],
                    "vehicle": _loads(spot["vehicle"], None),
                }
                for spot in spots
            ],
            "source_type": cache["source_type"] if cache else None,
            "source_path": cache["source_path"] if cache else None,
        }


    def save_map_to_db(self, parking: Parking, map_data: dict[str, Any]) -> None:
        """Сохраняет граф дорог/въезды из прежнего map JSON в таблицы."""
        parking_id = int(parking.id)

        self.db.execute(text("DELETE FROM road_edges WHERE parking_id = :parking_id"), {"parking_id": parking_id})
        self.db.execute(text("DELETE FROM entrances WHERE parking_id = :parking_id"), {"parking_id": parking_id})
        self.db.execute(
            text(
                """
                DELETE FROM road_vertices
                WHERE parking_id = :parking_id
                  AND COALESCE(is_spot, FALSE) = FALSE
                """
            ),
            {"parking_id": parking_id},
        )

        self.db.execute(
            text(
                """
                UPDATE parkings
                SET layout_meta = COALESCE(layout_meta, '{}'::jsonb) || CAST(:map_meta AS jsonb),
                    updated_at = NOW()
                WHERE id = :parking_id
                """
            ),
            {
                "parking_id": parking_id,
                "map_meta": _json({"map": {"parking": map_data.get("parking", {})}}, {}),
            },
        )

        client_to_vertex_id: dict[str, int] = {}

        existing_spot_vertices = self.db.execute(
            text(
                """
                SELECT
                    rv.id AS vertex_id,
                    rv.client_id AS vertex_client_id,
                    ps.client_id AS spot_client_id,
                    ps.spot_number AS spot_number,
                    ps.label AS spot_label
                FROM road_vertices rv
                LEFT JOIN parking_spots ps ON ps.road_vertex_id = rv.id
                WHERE rv.parking_id = :parking_id
                  AND COALESCE(rv.is_spot, FALSE) = TRUE
                """
            ),
            {"parking_id": parking_id},
        ).mappings().all()

        for vertex in existing_spot_vertices:
            vertex_id = int(vertex["vertex_id"])
            for alias_name in ["vertex_client_id", "spot_client_id", "spot_number", "spot_label"]:
                alias = vertex[alias_name]
                if alias is not None and str(alias) != "":
                    client_to_vertex_id[str(alias)] = vertex_id

        def add_vertex(vertex_payload: dict[str, Any], *, fallback_id: str, is_entrance: bool = False) -> int:
            client_id = _as_client_id(_get(vertex_payload, "id", "client_id", "vertex_id"), fallback_id)
            if client_id in client_to_vertex_id:
                return client_to_vertex_id[client_id]

            x, y = _point_from_item(vertex_payload)
            row = self.db.execute(
                text(
                    """
                    INSERT INTO road_vertices
                        (parking_id, client_id, x, y, label, is_spot, is_entrance, payload)
                    VALUES
                        (:parking_id, :client_id, :x, :y, :label, FALSE, :is_entrance, CAST(:payload AS jsonb))
                    RETURNING id
                    """
                ),
                {
                    "parking_id": parking_id,
                    "client_id": client_id,
                    "x": x,
                    "y": y,
                    "label": _get(vertex_payload, "label", "name"),
                    "is_entrance": is_entrance,
                    "payload": _json(vertex_payload, {}),
                },
            ).first()

            vertex_id = int(row[0])
            client_to_vertex_id[client_id] = vertex_id
            return vertex_id

        for index, vertex in enumerate(map_data.get("vertices") or map_data.get("road_vertices") or [], start=1):
            if not isinstance(vertex, dict):
                continue
            add_vertex(
                vertex,
                fallback_id=f"vertex_{index}",
                is_entrance=bool(vertex.get("is_entrance", False)),
            )

        for index, entrance in enumerate(map_data.get("entrances") or [], start=1):
            if not isinstance(entrance, dict):
                continue

            client_id = _as_client_id(_get(entrance, "id", "client_id"), f"entrance_{index}")
            x, y = _point_from_item(entrance)
            vertex_client_id = _as_client_id(
                _get(entrance, "road_vertex_client_id", "road_vertex_id", "vertex_id"),
                f"vertex_for_{client_id}",
            )
            vertex_id = add_vertex(
                {
                    "id": vertex_client_id,
                    "x": x,
                    "y": y,
                    "label": _get(entrance, "name", "label", default=f"Въезд {index}"),
                    "source": "entrance",
                    "entrance_id": client_id,
                },
                fallback_id=vertex_client_id,
                is_entrance=True,
            )

            self.db.execute(
                text(
                    """
                    INSERT INTO entrances
                        (parking_id, client_id, name, road_vertex_id, x, y, payload)
                    VALUES
                        (:parking_id, :client_id, :name, :road_vertex_id, :x, :y, CAST(:payload AS jsonb))
                    """
                ),
                {
                    "parking_id": parking_id,
                    "client_id": client_id,
                    "name": str(_get(entrance, "name", "label", default=f"Въезд {index}")),
                    "road_vertex_id": vertex_id,
                    "x": x,
                    "y": y,
                    "payload": _json(entrance, {}),
                },
            )

        for index, edge in enumerate(map_data.get("edges") or map_data.get("road_edges") or map_data.get("roads") or [], start=1):
            if not isinstance(edge, dict):
                continue

            source_client = str(_get(edge, "source", "from", "source_id", "from_id", default=""))
            destination_client = str(_get(edge, "destination", "to", "destination_id", "to_id", default=""))
            source_id = client_to_vertex_id.get(source_client)
            destination_id = client_to_vertex_id.get(destination_client)

            if not source_id or not destination_id or source_id == destination_id:
                continue

            length_meters = edge.get("length_meters") or edge.get("length") or edge.get("distance") or 1.0
            try:
                length_meters = max(float(length_meters), 0.01)
            except (TypeError, ValueError):
                length_meters = 1.0

            self.db.execute(
                text(
                    """
                    INSERT INTO road_edges
                        (parking_id, client_id, source, destination, length_meters, one_way, is_bidirectional, payload)
                    VALUES
                        (:parking_id, :client_id, :source, :destination, :length_meters,
                         :one_way, :is_bidirectional, CAST(:payload AS jsonb))
                    """
                ),
                {
                    "parking_id": parking_id,
                    "client_id": _as_client_id(_get(edge, "id", "client_id"), f"edge_{index}"),
                    "source": source_id,
                    "destination": destination_id,
                    "length_meters": length_meters,
                    "one_way": bool(edge.get("one_way", False)),
                    "is_bidirectional": bool(edge.get("is_bidirectional", not edge.get("one_way", False))),
                    "payload": _json(edge, {}),
                },
            )

        self.db.commit()

    def build_map_from_db(self, parking: Parking) -> dict[str, Any]:
        """Собирает прежний map JSON из таблиц road_vertices/road_edges/entrances."""
        layout = self.build_layout_from_db(parking)
        return {
            "parking": layout["parking"],
            "frame_meta": layout.get("frame_meta", {}),
            "entrances": layout.get("entrances", []),
            "vertices": layout.get("vertices", []),
            "edges": layout.get("edges", []),
        }

    def write_runtime_json_files(
        self,
        parking: Parking,
        layout_path: str | Path,
        occupancy_path: str | Path | None = None,
    ) -> None:
        """Собирает JSON-файлы из БД только для совместимости со старым детектором."""
        layout_file = Path(layout_path)
        layout_file.parent.mkdir(parents=True, exist_ok=True)
        layout_file.write_text(
            json.dumps(self.build_layout_from_db(parking), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        if occupancy_path:
            occupancy_file = Path(occupancy_path)
            occupancy_file.parent.mkdir(parents=True, exist_ok=True)
            occupancy_file.write_text(
                json.dumps(self.build_occupancy_from_db(parking), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
