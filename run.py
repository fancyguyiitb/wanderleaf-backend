#!/usr/bin/env python
"""Run the Django development server."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DJANGO_ENV = os.getenv("DJANGO_ENV", "development").lower().strip()
settings_module = "config.settings.prod" if DJANGO_ENV in {"production", "prod"} else "config.settings.dev"

os.environ.setdefault("DJANGO_ENV", DJANGO_ENV)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)


if __name__ == "__main__":
    from django.core.management import execute_from_command_line
    execute_from_command_line([sys.argv[0], "runserver"] + sys.argv[1:])
