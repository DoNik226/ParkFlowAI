import sys
from pathlib import Path
from unittest.mock import MagicMock

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

sys.modules['psycopg2'] = MagicMock()
sys.modules['psycopg2.extras'] = MagicMock()
sys.modules['psycopg2.pool'] = MagicMock()
sys.modules['sqlalchemy'] = MagicMock()
sys.modules['sqlalchemy.orm'] = MagicMock()
sys.modules['sqlalchemy.ext.declarative'] = MagicMock()
sys.modules['fastapi'] = MagicMock()
sys.modules['fastapi.security'] = MagicMock()
sys.modules['redis'] = MagicMock()
sys.modules['cv2'] = MagicMock()
sys.modules['ultralytics'] = MagicMock()
