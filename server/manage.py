#!/usr/bin/env python3
import os
import sys
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parent
REPO_DIR = SERVER_DIR.parent
sys.path.insert(0, str(REPO_DIR))
sys.path.insert(0, str(SERVER_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

from django.core.management import execute_from_command_line  # noqa: E402

if __name__ == "__main__":
    execute_from_command_line(sys.argv)
