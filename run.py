#!/usr/bin/env python
"""Run the Django development server."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
os.environ.setdefault("DJANGO_ENV", "development")

if __name__ == "__main__":
    from django.core.management import execute_from_command_line
    execute_from_command_line([sys.argv[0], "runserver"] + sys.argv[1:])
