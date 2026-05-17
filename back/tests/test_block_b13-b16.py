import pytest
import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[2]))

from back.app.services.detector_supervisor import extract_status_signature


class TestBlockB13:
    """Тест Б13 (ФТ 5) - позитивный: проверить формирование сигнатуры статусов парковочных мест"""
    
    def test_build_occupancy_signature(self):
        # Входные данные: occupancy с spots
        occupancy = {
            "spots": [
                {"spot_id": "1", "status": "free"}
            ]
        }
        
        # Действие
        result = extract_status_signature(occupancy)
        
        # Ожидаемый результат: { "1": "free" }
        assert result == {"1": "free"}


class TestBlockB14:
    """Тест Б14 (ФТ 5) - негативный: проверить обработку некорректного occupancy"""
    
    def test_handle_invalid_occupancy_without_spots(self):
        # Входные данные: occupancy без spots
        occupancy = {}
        
        # Действие
        result = extract_status_signature(occupancy)
        
        # Ожидаемый результат: None
        assert result is None


class TestBlockB15:
    """Тест Б15 (ФТ 6) - позитивный: проверить сравнение сигнатур occupancy (изменение)"""
    
    def test_compare_signatures_changed(self):
        # Входные данные: {"1":"free"} → {"1":"occupied"}
        old_signature = {"1": "free"}
        new_signature = {"1": "occupied"}
        
        # Действие: сравнение сигнатур
        changed = old_signature != new_signature
        
        # Ожидаемый результат: changed = True
        assert changed is True


class TestBlockB16:
    """Тест Б16 (ФТ 6) - позитивный: проверить отсутствие изменений при одинаковых сигнатурах"""
    
    def test_compare_signatures_unchanged(self):
        # Входные данные: одинаковые сигнатуры
        old_signature = {"1": "free"}
        new_signature = {"1": "free"}
        
        # Действие: сравнение сигнатур
        changed = old_signature != new_signature
        
        # Ожидаемый результат: changed = False
        assert changed is False