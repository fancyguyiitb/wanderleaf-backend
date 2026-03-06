"""
Wipe the database — delete all data, keep schema.

Usage:
    python manage.py shell < wipe_db.py
    # OR
    python wipe_db.py

If using wipe_db.py directly, it runs Django setup and executes flush.
"""

import os
import sys
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django
django.setup()

from django.core.management import call_command
from django.db import connection

def main():
    print("Wiping database...")
    call_command("flush", "--no-input")
    print("Database wiped. All tables emptied.")
    print("Run migrations and seed scripts to repopulate.")


if __name__ == "__main__":
    main()
