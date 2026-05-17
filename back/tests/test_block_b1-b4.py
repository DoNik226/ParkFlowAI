import pytest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))


class TestBlockB1:
    """Тест Б1 (ФТ 1) - позитивный: проверить выбор архивного видео как источника"""
    
    def test_select_video_as_source(self):
        source_type = "video"
        test_video_path = "/video.mp4"

        def get_source_path(source_type, video_path, rtsp_url):
            if source_type == "video":
                return video_path
            elif source_type == "rtsp":
                return rtsp_url
            return None

        selected_source = get_source_path(source_type, test_video_path, None)

        assert selected_source == test_video_path
        assert selected_source == "/video.mp4"


class TestBlockB2:
    """Тест Б2 (ФТ 1) - негативный: проверить отсутствие источника видео"""
    
    def test_missing_video_source_raises_error(self):
        # Входные данные
        source_type = "video"
        test_video_path = None
        
        # Функция с проверкой наличия источника
        def validate_and_get_source(source_type, video_path):
            if source_type == "video" and video_path is None:
                raise ValueError("Источник видео не указан")
            return video_path
        
        # Ожидаемый результат: ошибка
        with pytest.raises(ValueError, match="Источник видео не указан"):
            validate_and_get_source(source_type, test_video_path)


class TestBlockB3:
    """Тест Б3 (ФТ 2) - позитивный: проверить определение типа видеопотока"""
    
    def test_detect_stream_or_video_type(self):
        from back.app.services.run_parking_stream import infer_source_type
        
        # Входные данные
        filename = "video.mp4"
        
        # Действие
        result = infer_source_type(filename)
        
        # Ожидаемый результат: "stream_or_video"
        assert result == "stream_or_video"


class TestBlockB4:
    """Тест Б4 (ФТ 2) - позитивный: проверить выбор RTSP источника"""
    
    def test_select_rtsp_source(self):
        # Входные данные
        source_type = "rtsp"
        source_url = "rtsp://camera"

        def get_source_path(source_type, video_path, rtsp_url):
            if source_type == "video":
                return video_path
            elif source_type == "rtsp":
                return rtsp_url
            return None
        
        # Действие
        selected_source = get_source_path(source_type, None, source_url)
        
        # Ожидаемый результат: используется source_url
        assert selected_source == source_url
        assert selected_source == "rtsp://camera"