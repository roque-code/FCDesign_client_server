import os
import sys
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = SERVER_DIR.parent
sys.path.insert(0, str(REPO_DIR))
sys.path.insert(0, str(SERVER_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

from django.core.asgi import get_asgi_application  # noqa: E402

application = get_asgi_application()
