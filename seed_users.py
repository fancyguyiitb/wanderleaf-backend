"""
Seed script: register diverse sample users via the API.

Usage:
    1. Make sure the backend server is running.
    2. Run:  python seed_users.py

No access token needed — registration is a public endpoint.
All users are created with the password: Wanderleaf2026!
"""

import json
import requests

# ──────────────────────────────────────────────
#  CONFIG
# ──────────────────────────────────────────────
BASE_URL = "http://localhost:8000"
DEFAULT_PASSWORD = "Password123!"
# ──────────────────────────────────────────────

REGISTER_ENDPOINT = f"{BASE_URL}/api/v1/auth/register/"

USERS = [
    {
        "username": "Amara Okafor",
        "email": "amara.okafor@example.com",
        "phone_number": "+2348012345678",
    },
    {
        "username": "Liam Chen",
        "email": "liam.chen@example.com",
        "phone_number": "+14155551234",
    },
    {
        "username": "Sofia Rodríguez",
        "email": "sofia.rodriguez@example.com",
        "phone_number": "+5491123456789",
    },
    {
        "username": "Yuki Tanaka",
        "email": "yuki.tanaka@example.com",
        "phone_number": "+819012345678",
    },
    {
        "username": "Priya Sharma",
        "email": "priya.sharma@example.com",
        "phone_number": "+919876543210",
    },
    {
        "username": "Marcus Johansson",
        "email": "marcus.johansson@example.com",
        "phone_number": "+46701234567",
    },
    {
        "username": "Fatima Al-Rashid",
        "email": "fatima.alrashid@example.com",
        "phone_number": "+971501234567",
    },
    {
        "username": "Oliver Bennett",
        "email": "oliver.bennett@example.com",
        "phone_number": "+447911123456",
    },
    {
        "username": "Camille Dubois",
        "email": "camille.dubois@example.com",
        "phone_number": "+33612345678",
    },
    {
        "username": "Rafael Costa",
        "email": "rafael.costa@example.com",
        "phone_number": "+5511987654321",
    },
    {
        "username": "Anya Petrov",
        "email": "anya.petrov@example.com",
        "phone_number": "+79161234567",
    },
    {
        "username": "David Kim",
        "email": "david.kim@example.com",
        "phone_number": "+821012345678",
    },
    {
        "username": "Zara Mbeki",
        "email": "zara.mbeki@example.com",
        "phone_number": "+27821234567",
    },
    {
        "username": "Elena Vasquez",
        "email": "elena.vasquez@example.com",
        "phone_number": "+525512345678",
    },
    {
        "username": "Noah Williams",
        "email": "noah.williams@example.com",
        "phone_number": "+61412345678",
    },
]


def seed():
    created = 0
    failed = 0

    for i, user in enumerate(USERS, 1):
        payload = {**user, "password": DEFAULT_PASSWORD}
        resp = requests.post(
            REGISTER_ENDPOINT,
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
        )

        if resp.status_code == 201:
            data = resp.json()
            print(f"  [{i}/{len(USERS)}] Registered: {data['username']}  (id: {data['id']})")
            created += 1
        else:
            print(f"  [{i}/{len(USERS)}] FAILED: {user['username']}")
            print(f"           Status {resp.status_code}: {resp.text[:200]}")
            failed += 1

    print(f"\nDone — {created} registered, {failed} failed.")
    print(f"Password for all users: {DEFAULT_PASSWORD}")


if __name__ == "__main__":
    print(f"Registering {len(USERS)} users at {REGISTER_ENDPOINT}\n")
    seed()
