# back/app/services/map_routes.py
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from heapq import heappush, heappop
from collections import defaultdict
from sqlalchemy.orm import Session
from back.app.repositories.road_vertex_repository import RoadVertexRepository
from back.app.repositories.road_edge_repository import RoadEdgeRepository
from back.app.repositories.parking_spot_repository import ParkingSpotRepository
from back.app.models.road_vertex import RoadVertex
from back.app.models.road_edge import RoadEdge
from back.app.models.parking_spot import ParkingSpot


@dataclass
class RouteNode:
    """Узел маршрута"""
    vertex_id: int
    vertex_type: str  # 'entrance', 'spot', 'regular'
    spot_number: Optional[str] = None


@dataclass
class RouteEdge:
    """Ребро маршрута"""
    edge_id: int
    source: int
    destination: int
    length_meters: float


@dataclass
class RouteResponse:
    """Ответ с маршрутом"""
    path_nodes: List[RouteNode]
    path_edges: List[RouteEdge]
    total_distance_meters: float
    start_vertex_id: int
    end_vertex_id: int
    end_spot_number: Optional[str] = None


class MapRoutesService:
    """Сервис для построения маршрутов на парковке"""

    def __init__(self, db: Session):
        self.db = db
        self.vertex_repo = RoadVertexRepository(db)
        self.edge_repo = RoadEdgeRepository(db)
        self.spot_repo = ParkingSpotRepository(db)

    def _build_graph(self, parking_id: int) -> Tuple[Dict[int, List[Tuple[int, float, int]]], Dict[int, RoadVertex]]:
        """
        Строит граф для парковки в виде adjacency list

        Args:
            parking_id: ID парковки

        Returns:
            graph: {vertex_id: [(neighbor_id, distance, edge_id), ...]}
            vertices: {vertex_id: RoadVertex}
        """
        edges = self.edge_repo.get_graph_for_parking(parking_id)
        vertices_dict = {v.id: v for v in self.vertex_repo.get_by_parking(parking_id)}

        graph = defaultdict(list)

        for edge in edges:
            # Добавляем прямое ребро
            graph[edge.source].append((edge.destination, edge.length_meters, edge.id))

            # Если ребро двунаправленное, добавляем обратное
            if edge.is_bidirectional and not edge.one_way:
                graph[edge.destination].append((edge.source, edge.length_meters, edge.id))

        return graph, vertices_dict

    def _dijkstra(self, graph: Dict[int, List[Tuple[int, float, int]]],
                  start_id: int,
                  end_ids: List[int]) -> Tuple[Dict[int, float], Dict[int, int], Dict[int, int]]:
        """
        Алгоритм Дейкстры для поиска кратчайшего пути

        Args:
            graph: граф в виде adjacency list
            start_id: ID начальной вершины
            end_ids: список ID целевых вершин

        Returns:
            distances: {vertex_id: distance}
            previous: {vertex_id: previous_vertex_id}
            edge_used: {vertex_id: edge_id_used_to_reach}
        """
        distances = {start_id: 0}
        previous = {}
        edge_used = {}
        heap = [(0, start_id)]
        visited = set()

        # Множество целевых вершин для ранней остановки
        end_set = set(end_ids)

        while heap:
            current_dist, current = heappop(heap)

            if current in visited:
                continue

            visited.add(current)

            # Если достигли одной из целевых вершин, можно остановиться
            if current in end_set:
                break

            if current not in graph:
                continue

            for neighbor, weight, edge_id in graph[current]:
                new_dist = current_dist + weight

                if neighbor not in distances or new_dist < distances[neighbor]:
                    distances[neighbor] = new_dist
                    previous[neighbor] = current
                    edge_used[neighbor] = edge_id
                    heappush(heap, (new_dist, neighbor))

        return distances, previous, edge_used

    def _reconstruct_path(self, start_id: int, end_id: int,
                          previous: Dict[int, int],
                          edge_used: Dict[int, int],
                          vertices_dict: Dict[int, RoadVertex],
                          spot_by_vertex: Dict[int, ParkingSpot]) -> Tuple[List[RouteNode], List[RouteEdge]]:
        """
        Восстанавливает путь из результатов Дейкстры

        Args:
            start_id: ID начальной вершины
            end_id: ID конечной вершины
            previous: словарь предыдущих вершин
            edge_used: словарь использованных ребер
            vertices_dict: словарь вершин
            spot_by_vertex: словарь парковочных мест по vertex_id

        Returns:
            path_nodes: список узлов маршрута
            path_edges: список ребер маршрута
        """
        path_nodes = []
        path_edges = []

        current = end_id
        while current != start_id:
            # Добавляем узел
            vertex = vertices_dict.get(current)
            spot = spot_by_vertex.get(current)

            node_type = 'regular'
            if vertex and vertex.is_entrance:
                node_type = 'entrance'
            elif vertex and vertex.is_spot:
                node_type = 'spot'

            path_nodes.append(RouteNode(
                vertex_id=current,
                vertex_type=node_type,
                spot_number=spot.spot_number if spot else None
            ))

            # Добавляем ребро
            edge_id = edge_used.get(current)
            if edge_id:
                edge = self.db.query(RoadEdge).filter(RoadEdge.id == edge_id).first()
                if edge:
                    path_edges.append(RouteEdge(
                        edge_id=edge.id,
                        source=edge.source,
                        destination=edge.destination,
                        length_meters=edge.length_meters
                    ))

            current = previous.get(current)
            if current is None:
                break

        # Добавляем стартовую вершину
        start_vertex = vertices_dict.get(start_id)
        start_spot = spot_by_vertex.get(start_id)
        start_type = 'regular'
        if start_vertex and start_vertex.is_entrance:
            start_type = 'entrance'
        elif start_vertex and start_vertex.is_spot:
            start_type = 'spot'

        path_nodes.append(RouteNode(
            vertex_id=start_id,
            vertex_type=start_type,
            spot_number=start_spot.spot_number if start_spot else None
        ))

        # Разворачиваем пути, так как мы шли с конца
        path_nodes.reverse()
        path_edges.reverse()

        return path_nodes, path_edges

    def _get_vertex_id_for_spot(self, spot_id: int) -> Optional[int]:
        """Получает vertex_id для парковочного места"""
        spot = self.spot_repo.get(spot_id)
        if spot:
            return spot.road_vertex_id
        return None

    def _get_vertex_id_for_entrance(self, parking_id: int, entrance_id: int) -> Optional[int]:
        """Получает vertex_id для въезда"""
        entrances = self.vertex_repo.get_entrance_vertices(parking_id)
        for entrance in entrances:
            if entrance.id == entrance_id:
                return entrance.id
        return None

    def build_route_from_entrance_to_spot(self, parking_id: int,
                                          entrance_vertex_id: int,
                                          spot_vertex_id: int) -> Optional[RouteResponse]:
        """
        Строит маршрут от конкретного въезда до конкретного места

        Args:
            parking_id: ID парковки
            entrance_vertex_id: ID вершины въезда
            spot_vertex_id: ID вершины парковочного места

        Returns:
            RouteResponse или None, если маршрут не найден
        """
        # Проверяем, что вершины существуют и принадлежат парковке
        vertices = self.vertex_repo.get_by_parking(parking_id)
        vertex_ids = {v.id for v in vertices}

        if entrance_vertex_id not in vertex_ids or spot_vertex_id not in vertex_ids:
            return None

        # Получаем информацию о месте
        spot = self.db.query(ParkingSpot).filter(
            ParkingSpot.road_vertex_id == spot_vertex_id,
            ParkingSpot.parking_id == parking_id
        ).first()

        # Строим граф
        graph, vertices_dict = self._build_graph(parking_id)

        # Запускаем Дейкстру
        distances, previous, edge_used = self._dijkstra(graph, entrance_vertex_id, [spot_vertex_id])

        # Проверяем, достижимо ли место
        if spot_vertex_id not in distances:
            return None

        # Создаем mapping места к вершине
        spots = self.spot_repo.get_by_parking(parking_id)
        spot_by_vertex = {spot.road_vertex_id: spot for spot in spots if spot.road_vertex_id}

        # Восстанавливаем путь
        path_nodes, path_edges = self._reconstruct_path(
            entrance_vertex_id, spot_vertex_id, previous, edge_used, vertices_dict, spot_by_vertex
        )

        return RouteResponse(
            path_nodes=path_nodes,
            path_edges=path_edges,
            total_distance_meters=distances[spot_vertex_id],
            start_vertex_id=entrance_vertex_id,
            end_vertex_id=spot_vertex_id,
            end_spot_number=spot.spot_number if spot else None
        )

    def build_route_from_entrance_to_nearest_spot(self, parking_id: int,
                                                  entrance_vertex_id: int) -> Optional[RouteResponse]:
        """
        Строит маршрут от въезда до ближайшего свободного места

        Args:
            parking_id: ID парковки
            entrance_vertex_id: ID вершины въезда

        Returns:
            RouteResponse или None, если свободные места не найдены
        """
        # Получаем все свободные места
        free_spots = self.spot_repo.get_free_spots(parking_id)

        if not free_spots:
            return None

        # Получаем vertex_id для всех свободных мест
        spot_vertex_ids = [spot.road_vertex_id for spot in free_spots if spot.road_vertex_id]

        if not spot_vertex_ids:
            return None

        # Строим граф
        graph, vertices_dict = self._build_graph(parking_id)

        # Запускаем Дейкстру до всех свободных мест
        distances, previous, edge_used = self._dijkstra(graph, entrance_vertex_id, spot_vertex_ids)

        # Находим ближайшее достижимое место
        nearest_spot_id = None
        min_distance = float('inf')

        for spot_vertex_id in spot_vertex_ids:
            if spot_vertex_id in distances and distances[spot_vertex_id] < min_distance:
                min_distance = distances[spot_vertex_id]
                nearest_spot_id = spot_vertex_id

        if nearest_spot_id is None:
            return None

        # Находим информацию о месте
        spot = next((s for s in free_spots if s.road_vertex_id == nearest_spot_id), None)

        # Создаем mapping места к вершине
        spot_by_vertex = {spot.road_vertex_id: spot for spot in free_spots}

        # Восстанавливаем путь
        path_nodes, path_edges = self._reconstruct_path(
            entrance_vertex_id, nearest_spot_id, previous, edge_used, vertices_dict, spot_by_vertex
        )

        return RouteResponse(
            path_nodes=path_nodes,
            path_edges=path_edges,
            total_distance_meters=min_distance,
            start_vertex_id=entrance_vertex_id,
            end_vertex_id=nearest_spot_id,
            end_spot_number=spot.spot_number if spot else None
        )

    def build_route_from_nearest_entrance_to_spot(self, parking_id: int,
                                                  spot_vertex_id: int) -> Optional[RouteResponse]:
        """
        Строит маршрут от ближайшего въезда до указанного места

        Args:
            parking_id: ID парковки
            spot_vertex_id: ID вершины парковочного места

        Returns:
            RouteResponse или None, если въезды не найдены
        """
        # Получаем все въезды
        entrances = self.vertex_repo.get_entrance_vertices(parking_id)

        if not entrances:
            return None

        entrance_vertex_ids = [e.id for e in entrances]

        # Строим граф
        graph, vertices_dict = self._build_graph(parking_id)

        # Для каждого въезда находим расстояние до места
        best_entrance_id = None
        min_distance = float('inf')
        best_previous = None
        best_edge_used = None

        for entrance_id in entrance_vertex_ids:
            distances, previous, edge_used = self._dijkstra(graph, entrance_id, [spot_vertex_id])

            if spot_vertex_id in distances and distances[spot_vertex_id] < min_distance:
                min_distance = distances[spot_vertex_id]
                best_entrance_id = entrance_id
                best_previous = previous
                best_edge_used = edge_used

        if best_entrance_id is None:
            return None

        # Получаем информацию о месте
        spot = self.db.query(ParkingSpot).filter(
            ParkingSpot.road_vertex_id == spot_vertex_id,
            ParkingSpot.parking_id == parking_id
        ).first()

        # Создаем mapping места к вершине
        spots = self.spot_repo.get_by_parking(parking_id)
        spot_by_vertex = {spot.road_vertex_id: spot for spot in spots if spot.road_vertex_id}

        # Восстанавливаем путь
        path_nodes, path_edges = self._reconstruct_path(
            best_entrance_id, spot_vertex_id, best_previous, best_edge_used, vertices_dict, spot_by_vertex
        )

        return RouteResponse(
            path_nodes=path_nodes,
            path_edges=path_edges,
            total_distance_meters=min_distance,
            start_vertex_id=best_entrance_id,
            end_vertex_id=spot_vertex_id,
            end_spot_number=spot.spot_number if spot else None
        )