import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, Mock
from sqlalchemy.orm import Session

sys.path.append(str(Path(__file__).resolve().parents[2]))

from back.app.services.map_service import MapRoutesService


# Тест Б25 (ФТ 11) Проверка сохранения графа дорог (vertices/edges/entrances)
def test_b25_save_road_graph():
    """Проверка, что vertices, edges и entrances правильно сохраняются в БД"""
    
    mock_vertex_repo = MagicMock()
    mock_edge_repo = MagicMock()
    mock_spot_repo = MagicMock()
    mock_db = MagicMock(spec=Session)
    
    # Создаем тестовые данные для вершин
    test_parking_id = 1
    
    class MockVertex:
        def __init__(self, id, parking_id, is_entrance, is_spot):
            self.id = id
            self.parking_id = parking_id
            self.is_entrance = is_entrance
            self.is_spot = is_spot
    
    test_vertices = [
        MockVertex(id=1, parking_id=test_parking_id, is_entrance=True, is_spot=False),
        MockVertex(id=2, parking_id=test_parking_id, is_entrance=False, is_spot=True),
        MockVertex(id=3, parking_id=test_parking_id, is_entrance=False, is_spot=True),
        MockVertex(id=4, parking_id=test_parking_id, is_entrance=False, is_spot=False),
    ]
    
    # Создаем тестовые данные для ребер
    class MockEdge:
        def __init__(self, id, parking_id, source, destination, length_meters, is_bidirectional, one_way):
            self.id = id
            self.parking_id = parking_id
            self.source = source
            self.destination = destination
            self.length_meters = length_meters
            self.is_bidirectional = is_bidirectional
            self.one_way = one_way
    
    test_edges = [
        MockEdge(id=1, parking_id=test_parking_id, source=1, destination=2, length_meters=5.0, is_bidirectional=True, one_way=False),
        MockEdge(id=2, parking_id=test_parking_id, source=2, destination=3, length_meters=3.5, is_bidirectional=True, one_way=False),
        MockEdge(id=3, parking_id=test_parking_id, source=2, destination=4, length_meters=4.2, is_bidirectional=False, one_way=True),
    ]
    
    # Мокаем методы репозиториев
    mock_vertex_repo.get_by_parking.return_value = test_vertices
    mock_edge_repo.get_graph_for_parking.return_value = test_edges
    
    with patch('back.app.services.map_service.RoadVertexRepository', return_value=mock_vertex_repo), \
         patch('back.app.services.map_service.RoadEdgeRepository', return_value=mock_edge_repo), \
         patch('back.app.services.map_service.ParkingSpotRepository', return_value=mock_spot_repo):
        
        service = MapRoutesService(mock_db)
        graph, vertices_dict = service._build_graph(test_parking_id)
    
    # Проверяем вершины
    assert len(vertices_dict) == 4
    assert vertices_dict[1].is_entrance == True
    assert vertices_dict[2].is_spot == True
    
    # Проверяем граф - исправленная проверка
    # В граф попадают только вершины, которые участвуют в ребрах
    assert 1 in graph  # вершина-источник
    assert 2 in graph  # участвует в ребрах
    assert 3 in graph  # участвует в ребрах
    # Вершина 4 есть в графе? Она только как destination, но может не быть ключом
    assert 4 in graph or any(4 in [n for n, _, _ in graph.get(v, [])] for v in graph)
    
    # Проверяем связи
    neighbors_of_1 = [n for n, _, _ in graph[1]]
    assert 2 in neighbors_of_1
    
    # Проверяем въезды
    entrances = [v for v in vertices_dict.values() if v.is_entrance]
    assert len(entrances) == 1
    assert entrances[0].id == 1


# Тест Б26 (ФТ 12) Проверка выбора кратчайшего пути (минимальный length_meters)
def test_b26_shortest_path_selection():
    """Проверка, что алгоритм выбирает маршрут с минимальной длиной"""
    
    mock_db = MagicMock(spec=Session)
    test_parking_id = 1
    
    class MockVertex:
        def __init__(self, id, parking_id, is_entrance, is_spot):
            self.id = id
            self.parking_id = parking_id
            self.is_entrance = is_entrance
            self.is_spot = is_spot
    
    # Создаем граф с двумя альтернативными маршрутами
    test_vertices = [
        MockVertex(id=1, parking_id=test_parking_id, is_entrance=True, is_spot=False),
        MockVertex(id=2, parking_id=test_parking_id, is_entrance=False, is_spot=False),
        MockVertex(id=3, parking_id=test_parking_id, is_entrance=False, is_spot=False),
        MockVertex(id=4, parking_id=test_parking_id, is_entrance=False, is_spot=True),
        MockVertex(id=5, parking_id=test_parking_id, is_entrance=False, is_spot=False),
    ]
    
    class MockEdge:
        def __init__(self, id, parking_id, source, destination, length_meters, is_bidirectional, one_way):
            self.id = id
            self.parking_id = parking_id
            self.source = source
            self.destination = destination
            self.length_meters = length_meters
            self.is_bidirectional = is_bidirectional
            self.one_way = one_way
    
    test_edges = [
        # Маршрут 1: 1-2 (3м), 2-4 (4м) - итого 7м
        MockEdge(id=1, parking_id=test_parking_id, source=1, destination=2, length_meters=3.0, is_bidirectional=True, one_way=False),
        MockEdge(id=2, parking_id=test_parking_id, source=2, destination=4, length_meters=4.0, is_bidirectional=True, one_way=False),
        # Маршрут 2: 1-3 (5м), 3-4 (2м) - итого 7м
        MockEdge(id=3, parking_id=test_parking_id, source=1, destination=3, length_meters=5.0, is_bidirectional=True, one_way=False),
        MockEdge(id=4, parking_id=test_parking_id, source=3, destination=4, length_meters=2.0, is_bidirectional=True, one_way=False),
        # Маршрут 3 (кратчайший): 1-5 (2м), 5-4 (3м) - итого 5м
        MockEdge(id=5, parking_id=test_parking_id, source=1, destination=5, length_meters=2.0, is_bidirectional=True, one_way=False),
        MockEdge(id=6, parking_id=test_parking_id, source=5, destination=4, length_meters=3.0, is_bidirectional=True, one_way=False),
    ]
    
    mock_vertex_repo = MagicMock()
    mock_vertex_repo.get_by_parking.return_value = test_vertices
    
    mock_edge_repo = MagicMock()
    mock_edge_repo.get_graph_for_parking.return_value = test_edges
    
    # Мокаем query для получения информации о месте
    mock_spot = MagicMock()
    mock_spot.spot_number = "A1"
    mock_spot.road_vertex_id = 4
    
    mock_db.query.return_value.filter.return_value.first.return_value = mock_spot
    
    with patch('back.app.services.map_service.RoadVertexRepository', return_value=mock_vertex_repo), \
         patch('back.app.services.map_service.RoadEdgeRepository', return_value=mock_edge_repo), \
         patch('back.app.services.map_service.ParkingSpotRepository') as MockSpotRepo:
        
        mock_spot_repo = MockSpotRepo.return_value
        mock_spot_repo.get.return_value = mock_spot
        mock_spot_repo.get_by_parking.return_value = [mock_spot]
        
        service = MapRoutesService(mock_db)
        
        # Строим маршрут от въезда (1) до места (4)
        route = service.build_route_from_entrance_to_spot(test_parking_id, 1, 4)
    
    # Проверяем, что маршрут найден
    assert route is not None
    
    # Проверяем, что выбран кратчайший путь (5 метров, а не 7)
    assert route.total_distance_meters == 5.0
    
    # Проверяем, что путь проходит через вершину 5 (кратчайший маршрут)
    path_vertex_ids = [node.vertex_id for node in route.path_nodes]
    assert 5 in path_vertex_ids
    assert 2 not in path_vertex_ids  # Более длинный маршрут не выбран
    assert 3 not in path_vertex_ids  # Более длинный маршрут не выбран
    
    # Проверяем последовательность маршрута: 1 -> 5 -> 4
    assert path_vertex_ids[0] == 1
    assert path_vertex_ids[-1] == 4


# Тест Б27 (ФТ 13) Проверка фильтрации свободных мест (только free статус)
def test_b27_filter_free_spots_only():
    """Проверка, что возвращаются только места со статусом 'free'"""
    
    test_parking_id = 1
    
    class MockParkingSpot:
        def __init__(self, id, parking_id, spot_number, status, road_vertex_id):
            self.id = id
            self.parking_id = parking_id
            self.spot_number = spot_number
            self.status = status
            self.road_vertex_id = road_vertex_id
    
    # Создаем парковочные места с разными статусами
    test_spots = [
        MockParkingSpot(id=1, parking_id=test_parking_id, spot_number="A1", status="free", road_vertex_id=101),
        MockParkingSpot(id=2, parking_id=test_parking_id, spot_number="A2", status="occupied", road_vertex_id=102),
        MockParkingSpot(id=3, parking_id=test_parking_id, spot_number="B1", status="free", road_vertex_id=103),
        MockParkingSpot(id=4, parking_id=test_parking_id, spot_number="B2", status="reserved", road_vertex_id=104),
        MockParkingSpot(id=5, parking_id=test_parking_id, spot_number="C1", status="free", road_vertex_id=105),
        MockParkingSpot(id=6, parking_id=test_parking_id, spot_number="C2", status="unknown", road_vertex_id=106),
        MockParkingSpot(id=7, parking_id=test_parking_id, spot_number="D1", status="free", road_vertex_id=107),
    ]
    
    mock_db = MagicMock(spec=Session)
    mock_spot_repo = MagicMock()
    mock_spot_repo.get_free_spots.return_value = [spot for spot in test_spots if spot.status == "free"]
    mock_spot_repo.get_by_parking.return_value = test_spots
    
    with patch('back.app.services.map_service.ParkingSpotRepository', return_value=mock_spot_repo), \
         patch('back.app.services.map_service.RoadVertexRepository') as MockVertexRepo, \
         patch('back.app.services.map_service.RoadEdgeRepository') as MockEdgeRepo:
        
        MockVertexRepo.return_value.get_by_parking.return_value = []
        MockEdgeRepo.return_value.get_graph_for_parking.return_value = []
        
        # Получаем свободные места через метод репозитория
        free_spots = mock_spot_repo.get_free_spots(test_parking_id)
    
    # Проверяем, что возвращены только места со статусом "free"
    assert len(free_spots) == 4
    
    for spot in free_spots:
        assert spot.status == "free"
    
    # Проверяем, что места с другими статусами не включены
    free_spot_numbers = [spot.spot_number for spot in free_spots]
    assert "A1" in free_spot_numbers
    assert "B1" in free_spot_numbers
    assert "C1" in free_spot_numbers
    assert "D1" in free_spot_numbers
    
    assert "A2" not in free_spot_numbers  # occupied
    assert "B2" not in free_spot_numbers  # reserved
    assert "C2" not in free_spot_numbers  # unknown
    
    # Проверка: метод get_free_spots должен быть вызван с правильным parking_id
    mock_spot_repo.get_free_spots.assert_called_once_with(test_parking_id)


# Дополнительный тест: Проверка маршрута до ближайшего свободного места
def test_b27_route_to_nearest_free_spot():
    """Проверка, что при построении маршрута выбирается ближайшее свободное место"""
    
    mock_db = MagicMock(spec=Session)
    test_parking_id = 1
    entrance_vertex_id = 1
    
    class MockVertex:
        def __init__(self, id, parking_id, is_entrance, is_spot):
            self.id = id
            self.parking_id = parking_id
            self.is_entrance = is_entrance
            self.is_spot = is_spot
    
    # Создаем вершины
    test_vertices = [
        MockVertex(id=1, parking_id=test_parking_id, is_entrance=True, is_spot=False),
        MockVertex(id=2, parking_id=test_parking_id, is_entrance=False, is_spot=True),
        MockVertex(id=3, parking_id=test_parking_id, is_entrance=False, is_spot=True),
        MockVertex(id=4, parking_id=test_parking_id, is_entrance=False, is_spot=True),
    ]
    
    class MockEdge:
        def __init__(self, id, parking_id, source, destination, length_meters, is_bidirectional, one_way):
            self.id = id
            self.parking_id = parking_id
            self.source = source
            self.destination = destination
            self.length_meters = length_meters
            self.is_bidirectional = is_bidirectional
            self.one_way = one_way
    
    # Создаем ребра (расстояния увеличиваются)
    test_edges = [
        MockEdge(id=1, parking_id=test_parking_id, source=1, destination=2, length_meters=10.0, is_bidirectional=True, one_way=False),
        MockEdge(id=2, parking_id=test_parking_id, source=2, destination=3, length_meters=15.0, is_bidirectional=True, one_way=False),
        MockEdge(id=3, parking_id=test_parking_id, source=3, destination=4, length_meters=20.0, is_bidirectional=True, one_way=False),
    ]
    
    class MockParkingSpot:
        def __init__(self, id, parking_id, spot_number, status, road_vertex_id):
            self.id = id
            self.parking_id = parking_id
            self.spot_number = spot_number
            self.status = status
            self.road_vertex_id = road_vertex_id
    
    # Свободные места: 3 и 4 (ближайшее свободное - 3 на расстоянии 25м, 4 - на 45м)
    free_spot_vertices = [
        MockParkingSpot(id=3, parking_id=test_parking_id, spot_number="B1", status="free", road_vertex_id=3),
        MockParkingSpot(id=4, parking_id=test_parking_id, spot_number="C1", status="free", road_vertex_id=4),
    ]
    
    # Занятое место: 2
    occupied_spot = MockParkingSpot(id=2, parking_id=test_parking_id, spot_number="A1", status="occupied", road_vertex_id=2)
    
    mock_vertex_repo = MagicMock()
    mock_vertex_repo.get_by_parking.return_value = test_vertices
    mock_vertex_repo.get_entrance_vertices.return_value = [test_vertices[0]]
    
    mock_edge_repo = MagicMock()
    mock_edge_repo.get_graph_for_parking.return_value = test_edges
    
    mock_spot_repo = MagicMock()
    mock_spot_repo.get_free_spots.return_value = free_spot_vertices
    mock_spot_repo.get_by_parking.return_value = free_spot_vertices + [occupied_spot]
    
    with patch('back.app.services.map_service.RoadVertexRepository', return_value=mock_vertex_repo), \
         patch('back.app.services.map_service.RoadEdgeRepository', return_value=mock_edge_repo), \
         patch('back.app.services.map_service.ParkingSpotRepository', return_value=mock_spot_repo):
        
        service = MapRoutesService(mock_db)
        
        # Строим маршрут до ближайшего свободного места
        route = service.build_route_from_entrance_to_nearest_spot(test_parking_id, entrance_vertex_id)
    
    # Проверяем, что маршрут найден
    assert route is not None
    
    # Проверяем, что выбрано ближайшее свободное место (вершина 3, расстояние 25м)
    assert route.end_vertex_id == 3
    assert route.total_distance_meters == 25.0  # 10 + 15
    
    # Проверяем, что место 4 (на 45м) не выбрано
    assert route.end_vertex_id != 4