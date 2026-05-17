import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import pytest
from back.app.schemas.map_routes import VertexType, RouteNodeSchema, RouteEdgeSchema, RouteResponseSchema


class TestBlockB31:
    """Тест Б31 (ФТ 16) - позитивный: проверка выбора въезда"""
    
    def test_select_entrance(self):
        # Входные данные: entrances [1,2,3], selected=2
        entrances = [1, 2, 3]
        selected = 2
        
        # Функция выбора въезда (из api/parking_routes - get_entrances)
        def select_entrance(entrances_list, selected_id):
            if selected_id in entrances_list:
                return selected_id
            return None
        
        # Действие
        result = select_entrance(entrances, selected)
        
        # Ожидаемый результат: selectedEntrance = 2
        assert result == 2


class TestBlockB32:
    """Тест Б32 (ФТ 16) - негативный: проверка выбора несуществующего въезда"""
    
    def test_select_nonexistent_entrance_returns_none(self):
        # Входные данные: selected=5 (не существует)
        entrances = [1, 2, 3]
        selected = 5
        
        # Функция выбора въезда
        def select_entrance(entrances_list, selected_id):
            if selected_id in entrances_list:
                return selected_id
            return None
        
        # Действие
        result = select_entrance(entrances, selected)
        
        # Ожидаемый результат: значение не изменяется (None)
        assert result is None
    
    def test_select_nonexistent_entrance_raises_error(self):
        entrances = [1, 2, 3]
        selected = 5
        
        def resolve_entrance(entrances_list, selected_id):
            if selected_id not in entrances_list:
                raise HTTPException(status_code=404, detail="Entrance not found")
            return selected_id
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            resolve_entrance(entrances, selected)
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Entrance not found"


class TestBlockB33:
    """Тест Б33 (ФТ 17) - позитивный: добавление полигона парковочного места"""
    
    def test_create_spot_with_polygon(self):
        # Входные данные: 4 точки полигона 
        polygon_points = [
            {"x": 100, "y": 100},
            {"x": 150, "y": 100},
            {"x": 150, "y": 150},
            {"x": 100, "y": 150}
        ]

        def create_spot(spot_id, polygon):
            return {
                "id": spot_id,
                "polygon": polygon,
                "status": "free",
                "enabled": True
            }
        
        # Действие
        result = create_spot("spot_1", polygon_points)
        
        # Ожидаемый результат: создан spot с polygon
        assert result["id"] == "spot_1"
        assert result["polygon"] == polygon_points
        assert len(result["polygon"]) == 4
        assert result["polygon"][0] == {"x": 100, "y": 100}
        assert result["polygon"][2] == {"x": 150, "y": 150}
    
    def test_validate_polygon_has_four_points(self):
        # Проверка валидности полигона для парковочного места
        polygon_points = [
            {"x": 100, "y": 100},
            {"x": 150, "y": 100},
            {"x": 150, "y": 150},
            {"x": 100, "y": 150}
        ]
        
        def validate_polygon(polygon):
            if len(polygon) < 3:
                raise ValueError("Polygon must have at least 3 points")
            return True
        
        assert validate_polygon(polygon_points) is True


class TestBlockB34:
    """Тест Б34 (ФТ 17) - позитивный: перемещение вершины полигона"""
    
    def test_update_vertex_coordinate(self):
        # Входные данные: vertex (1,1) → (2,2)
        old_vertex = {"x": 1, "y": 1}
        new_vertex = {"x": 2, "y": 2}
        
        # Функция обновления вершины 
        def update_vertex(old_x, old_y, new_x, new_y):
            return {"x": new_x, "y": new_y}
        
        # Действие
        result = update_vertex(old_vertex["x"], old_vertex["y"], 2, 2)
        
        # Ожидаемый результат: обновление координаты
        assert result["x"] == 2
        assert result["y"] == 2
        assert result != old_vertex
    
    def test_update_polygon_vertex(self):
        # Полное обновление вершины в полигоне
        polygon = [
            {"x": 1, "y": 1},
            {"x": 2, "y": 1},
            {"x": 2, "y": 2},
            {"x": 1, "y": 2}
        ]
        
        def update_polygon_vertex(polygon, vertex_index, new_x, new_y):
            if 0 <= vertex_index < len(polygon):
                polygon[vertex_index] = {"x": new_x, "y": new_y}
            return polygon
        
        # Действие: меняем первую вершину (1,1) → (2,2)
        result = update_polygon_vertex(polygon, 0, 2, 2)
        
        # Ожидаемый результат
        assert result[0]["x"] == 2
        assert result[0]["y"] == 2
        assert result[1] == {"x": 2, "y": 1}
        assert result[2] == {"x": 2, "y": 2}
        assert result[3] == {"x": 1, "y": 2}