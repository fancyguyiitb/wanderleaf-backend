"""
Django settings module selector.

Reads DJANGO_ENV from environment variables to determine which settings to use.
Defaults to 'development' if not set.

Set DJANGO_ENV=production in your .env file to use production settings.
Set DJANGO_ENV=development (or leave unset) to use development settings.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

# Get environment flag (defaults to 'development')
DJANGO_ENV = os.getenv("DJANGO_ENV", "development").lower().strip()

# Select settings module based on environment
if DJANGO_ENV == "production":
    from .prod import *  # noqa
else:
    from .dev import *  # noqa

