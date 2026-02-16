import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables to check DJANGO_ENV
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Determine settings module based on DJANGO_ENV flag
DJANGO_ENV = os.getenv("DJANGO_ENV", "development").lower().strip()
if DJANGO_ENV == "production":
    settings_module = "config.settings.prod"
else:
    settings_module = "config.settings.dev"

os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()

