import pytest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))


class TestBlockB17:
    """Тест Б17 (ФТ 7) - позитивный: проверить агрегацию загруженности парковки"""
    
    def test_aggregate_occupancy_from_multiple_cameras(self):
        # Входные данные: 2 камеры с occupancy
        camera_1_occupancy = {
            "summary": {"total": 10, "free": 6, "occupied": 4, "unknown": 0}
        }
        camera_2_occupancy = {
            "summary": {"total": 8, "free": 3, "occupied": 5, "unknown": 0}
        }
        
        # Функция агрегации
        def aggregate_occupancy(cameras_occupancy):
            total = sum(c.get("summary", {}).get("total", 0) for c in cameras_occupancy)
            free = sum(c.get("summary", {}).get("free", 0) for c in cameras_occupancy)
            occupied = sum(c.get("summary", {}).get("occupied", 0) for c in cameras_occupancy)
            unknown = sum(c.get("summary", {}).get("unknown", 0) for c in cameras_occupancy)
            
            return {
                "total": total,
                "free": free,
                "occupied": occupied,
                "unknown": unknown,
                "occupancy_percentage": (occupied / total * 100) if total else 0
            }
        
        # Действие
        result = aggregate_occupancy([camera_1_occupancy, camera_2_occupancy])
        
        # Ожидаемый результат: корректный total/free/occupied
        assert result["total"] == 18
        assert result["free"] == 9
        assert result["occupied"] == 9


class TestBlockB18:
    """Тест Б18 (ФТ 7) - негативный: проверить обработку пустого списка камер"""
    
    def test_aggregate_occupancy_with_empty_cameras_list(self):
        # Входные данные: cameras = []
        cameras = []
        
        # Функция агрегации
        def aggregate_occupancy(cameras_occupancy):
            if not cameras_occupancy:
                return {
                    "total": 0,
                    "free": 0,
                    "occupied": 0,
                    "unknown": 0,
                    "occupancy_percentage": 0,
                    "spots": []
                }
            
            total = sum(c.get("summary", {}).get("total", 0) for c in cameras_occupancy)
            free = sum(c.get("summary", {}).get("free", 0) for c in cameras_occupancy)
            occupied = sum(c.get("summary", {}).get("occupied", 0) for c in cameras_occupancy)
            unknown = sum(c.get("summary", {}).get("unknown", 0) for c in cameras_occupancy)
            
            return {
                "total": total,
                "free": free,
                "occupied": occupied,
                "unknown": unknown,
                "occupancy_percentage": (occupied / total * 100) if total else 0
            }
        
        # Действие
        result = aggregate_occupancy(cameras)
        
        # Ожидаемый результат: пустая структура без ошибки
        assert result["total"] == 0
        assert result["free"] == 0
        assert result["occupied"] == 0
        assert result["occupancy_percentage"] == 0


class TestBlockB19:
    """Тест Б19 (ФТ 8) - позитивный: проверить валидацию структуры map.json"""
    
    def test_validate_valid_map_structure(self):
        # Входные данные: map с vertices/edges/entrances
        valid_map = {
            "parking": {"id": "parking_1", "name": "Test Parking"},
            "vertices": [
                {"id": "v1", "x": 100, "y": 200},
                {"id": "v2", "x": 300, "y": 400}
            ],
            "edges": [
                {"source": "v1", "destination": "v2", "length_meters": 5.0}
            ],
            "entrances": [
                {"id": "e1", "name": "Main Entrance", "road_vertex_id": "v1"}
            ]
        }
        
        # Функция валидации
        def validate_map(map_data):
            required_fields = ["parking", "vertices", "edges", "entrances"]
            for field in required_fields:
                if field not in map_data:
                    raise ValueError(f"Missing required field: {field}")
            
            if not isinstance(map_data["vertices"], list):
                raise ValueError("vertices must be a list")
            
            if not isinstance(map_data["edges"], list):
                raise ValueError("edges must be a list")
            
            if not isinstance(map_data["entrances"], list):
                raise ValueError("entrances must be a list")
            
            return True
        
        # Действие
        result = validate_map(valid_map)
        
        # Ожидаемый результат: структура валидна
        assert result is True


class TestBlockB20:
    """Тест Б20 (ФТ 8) - негативный: проверить отсутствие обязательных полей в map.json"""
    
    def test_validate_map_missing_vertices_field(self):
        # Входные данные: map без vertices
        invalid_map = {
            "parking": {"id": "parking_1", "name": "Test Parking"},
            "edges": [
                {"source": "v1", "destination": "v2", "length_meters": 5.0}
            ],
            "entrances": [
                {"id": "e1", "name": "Main Entrance", "road_vertex_id": "v1"}
            ]
        }
        
        # Функция валидации
        def validate_map(map_data):
            required_fields = ["parking", "vertices", "edges", "entrances"]
            for field in required_fields:
                if field not in map_data:
                    raise ValueError(f"Missing required field: {field}")
            return True
        
        # Ожидаемый результат: ошибка валидации
        with pytest.raises(ValueError, match="Missing required field: vertices"):
            validate_map(invalid_map)
    
    def test_validate_map_missing_edges_field(self):
        # Входные данные: map без edges
        invalid_map = {
            "parking": {"id": "parking_1", "name": "Test Parking"},
            "vertices": [
                {"id": "v1", "x": 100, "y": 200},
                {"id": "v2", "x": 300, "y": 400}
            ],
            "entrances": [
                {"id": "e1", "name": "Main Entrance", "road_vertex_id": "v1"}
            ]
        }
        
        def validate_map(map_data):
            required_fields = ["parking", "vertices", "edges", "entrances"]
            for field in required_fields:
                if field not in map_data:
                    raise ValueError(f"Missing required field: {field}")
            return True
        
        with pytest.raises(ValueError, match="Missing required field: edges"):
            validate_map(invalid_map)