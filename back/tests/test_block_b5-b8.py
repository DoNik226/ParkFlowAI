import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from unittest.mock import Mock, patch
import pytest

from back.app.services.run_parking_stream import (
    infer_source_type,
    process_and_maybe_update,
)


class TestBlockB5:
    """Тест Б5 (ФТ 3) - позитивный: проверить определение типа источника изображения"""
    
    def test_detect_image_source_type(self):
        source = "image.jpg"
        result = infer_source_type(source)
        assert result == "image"


class TestBlockB6:
    """Тест Б6 (ФТ 3) - позитивный: проверить вызов process_frame при обработке кадра"""
    
    def test_process_frame_called_with_correct_arguments(self):
        mock_process_frame = Mock(return_value=({"spots": []}, "debug_frame"))
        
        with patch("back.app.services.run_parking_stream.process_frame", mock_process_frame):
            process_and_maybe_update(
                model="model",
                layout={},
                frame="frame_data",
                source="video.mp4",
                frame_index=1,
                timestamp_sec=0.5,
                detection_args={},
                output_json="occupancy.json",
                debug_frame_path=None,
                previous_signature=None,
                write_debug_every_frame=False,
            )
        
        mock_process_frame.assert_called_once_with(
            model="model",
            frame="frame_data",
            layout={},
            source_path="video.mp4",
            frame_index=1,
            timestamp_sec=0.5,
            args={},
        )


class TestBlockB7:
    """Тест Б7 (ФТ 3) - позитивный: проверить запись occupancy после обработки кадра"""
    
    def test_atomic_write_json_called_when_occupancy_changed(self):
        occupancy = {"spots": [{"spot_id": 1, "status": "occupied"}]}
        
        with patch("back.app.services.run_parking_stream.process_frame", return_value=(occupancy, "debug_frame")):
            with patch("back.app.services.run_parking_stream.atomic_write_json") as mock_atomic_write_json:
                process_and_maybe_update(
                    model="model",
                    layout={},
                    frame="frame_data",
                    source="video.mp4",
                    frame_index=1,
                    timestamp_sec=0.5,
                    detection_args={},
                    output_json="occupancy.json",
                    debug_frame_path=None,
                    previous_signature=None,
                    write_debug_every_frame=False,
                )
        
        mock_atomic_write_json.assert_called_once_with(occupancy, "occupancy.json")


class TestBlockB8:
    """Тест Б8 (ФТ 3) - негативный: проверить обработку ошибки детекции"""
    
    def test_detection_error_raises_exception(self):
        
        with patch("back.app.services.run_parking_stream.process_frame", side_effect=Exception("Detection failed")):
            # Ожидаем, что исключение будет выброшено
            with pytest.raises(Exception, match="Detection failed"):
                process_and_maybe_update(
                    model="model",
                    layout={},
                    frame="frame_data",
                    source="video.mp4",
                    frame_index=1,
                    timestamp_sec=0.5,
                    detection_args={},
                    output_json="occupancy.json",
                    debug_frame_path=None,
                    previous_signature=None,
                    write_debug_every_frame=False,
                )