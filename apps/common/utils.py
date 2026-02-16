"""
Common utility functions for the project.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables once
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


def get_django_env() -> str:
    """
    Get the current Django environment from DJANGO_ENV env variable.
    
    Returns:
        str: 'production' or 'development' (defaults to 'development')
    """
    return os.getenv("DJANGO_ENV", "development").lower().strip()


def is_production() -> bool:
    """
    Check if the current environment is production.
    
    Returns:
        bool: True if DJANGO_ENV=production, False otherwise
    """
    return get_django_env() == "production"


def is_development() -> bool:
    """
    Check if the current environment is development.
    
    Returns:
        bool: True if DJANGO_ENV=development (or not set), False otherwise
    """
    return get_django_env() == "development"
