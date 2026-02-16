#!/usr/bin/env python
"""
Quick script to verify Cloudinary configuration is working.
Run: python check_cloudinary_config.py
"""
import os
import sys
import django
from pathlib import Path

from dotenv import load_dotenv

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))

# Load .env so this script sees the same environment as `manage.py`
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Prefer whatever is set in env, otherwise use the selector module.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", os.getenv("DJANGO_SETTINGS_MODULE", "config.settings"))

try:
    django.setup()
except Exception as e:
    print(f"❌ Error loading Django settings: {e}")
    print("\nThis might be because Cloudinary credentials are missing from .env")
    sys.exit(1)

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.storage import storages

print("=" * 60)
print("Cloudinary Configuration Check")
print("=" * 60)

print(f"\n✅ DJANGO_SETTINGS_MODULE: {os.environ.get('DJANGO_SETTINGS_MODULE')}")
print(f"✅ DJANGO_ENV from env: {os.environ.get('DJANGO_ENV')}")

print(f"\n✅ Has CLOUDINARY_STORAGE: {hasattr(settings, 'CLOUDINARY_STORAGE')}")

if hasattr(settings, 'CLOUDINARY_STORAGE'):
    print(f"   Cloud Name: {settings.CLOUDINARY_STORAGE.get('CLOUD_NAME')}")
    print(f"   API Key: {settings.CLOUDINARY_STORAGE.get('API_KEY', '')[:8]}...")
    print(f"   Secure: {settings.CLOUDINARY_STORAGE.get('SECURE', False)}")
else:
    print("   ⚠️  CLOUDINARY_STORAGE not found in settings!")

# Check storage backend
try:
    print(f"\n✅ Default storage class: {type(default_storage).__name__}")
    print(f"   Module: {type(default_storage).__module__}")

    # `default_storage` is a lazy wrapper; show the real backend via `storages["default"]`
    backend = storages["default"]
    backend_str = f"{type(backend).__module__}.{type(backend).__name__}"
    print(f"   Resolved backend (storages['default']): {backend_str}")

    if "cloudinary_storage" in backend_str.lower():
        print("   ✅ Using Cloudinary storage!")
    else:
        print("   ⚠️  NOT using Cloudinary storage - check your settings!")
        print("   Expected backend to include 'cloudinary_storage'")
except Exception as e:
    print(f"\n❌ Error checking storage: {e}")

print("\n" + "=" * 60)
