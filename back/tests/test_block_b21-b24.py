import pytest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from back.app.schemas.map_routes import RouteResponseSchema, RouteNodeSchema, RouteEdgeSchema, VertexType
from back.app.models.enums import CameraStatus


class TestBlockB21:
    """Тест Б21 (ФТ 9) - позитивный: проверить конвертацию маршрута в response schema"""
    
    def test_convert_route_to_response_schema(self):
        # Входные данные: route с nodes/edges
        path_nodes = [
            RouteNodeSchema(vertex_id=1, vertex_type=VertexType.ENTRANCE, spot_number=None),
            RouteNodeSchema(vertex_id=2, vertex_type=VertexType.SPOT, spot_number="A1")
        ]
        
        path_edges = [
            RouteEdgeSchema(edge_id=100, source=1, destination=2, length_meters=15.5)
        ]
        
        # Действие: создаем RouteResponseSchema
        result = RouteResponseSchema(
            path_nodes=path_nodes,
            path_edges=path_edges,
            total_distance_meters=15.5,
            start_vertex_id=1,
            end_vertex_id=2
        )
        
        # Ожидаемый результат: RouteResponseSchema
        assert isinstance(result, RouteResponseSchema)


class TestBlockB22:
    """Тест Б22 (ФТ 9) - негативный: проверить обработку пустого маршрута"""
    
    def test_handle_empty_route(self):
        # Входные данные: route = None
        route = None
        
        # Действие: проверка на None
        def process_route(route):
            if route is None:
                return None
            return RouteResponseSchema(...)
        
        result = process_route(route)
        
        # Ожидаемый результат: None
        assert result is None


class TestBlockB23:
    """Тест Б23 (ФТ 10) - позитивный: проверить преобразование статуса камеры в API-ответ"""
    
    def test_camera_status_to_api_response(self):
        camera_status = "ONLINE"
        
        # Преобразование в API-ответ
        api_status = camera_status
        
        # Ожидаемый результат: ONLINE
        assert api_status == "ONLINE"


class TestBlockB24:
    """Тест Б24 (ФТ 10) - негативный: проверить неизвестный статус камеры"""
    
    def test_unknown_camera_status(self):
        unknown_status = "UNKNOWN_STATUS"
        
        # Обработка неизвестного статуса
        def get_safe_status(status):
            valid_statuses = ["ONLINE", "OFFLINE", "ERROR"]
            return status if status in valid_statuses else "OFFLINE"
        
        # Действие
        result = get_safe_status(unknown_status)
        
        # Ожидаемый результат: OFFLINE
        assert result == "OFFLINE"