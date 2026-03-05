"""
Seed script: register Indian sample users via the API.

Usage:
    1. Make sure the backend server is running.
    2. Run:  python seed_users.py

No access token needed — registration is a public endpoint.
All users are created with the password: Password123!
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
    {"username": "Sarthak Niranjan", "email": "sarthak.niranjan@example.com", "phone_number": "+919876543210"},
    {"username": "Arjun Singh", "email": "arjun.singh@example.com", "phone_number": "+919123456789"},
    {"username": "Riya Kapoor", "email": "riya.kapoor@example.com", "phone_number": "+919845678901"},
    {"username": "Karthik Iyer", "email": "karthik.iyer@example.com", "phone_number": "+919998877665"},
    {"username": "Meenakshi Nair", "email": "meenakshi.nair@example.com", "phone_number": "+919112233445"},
    {"username": "Vikram Mehta", "email": "vikram.mehta@example.com", "phone_number": "+919778899001"},
    {"username": "Anjali Gupta", "email": "anjali.gupta@example.com", "phone_number": "+919334455667"},
    {"username": "Sameer Desai", "email": "sameer.desai@example.com", "phone_number": "+919556677889"},
    {"username": "Pooja Joshi", "email": "pooja.joshi@example.com", "phone_number": "+919667788990"},
    {"username": "Rahul Chatterjee", "email": "rahul.chatterjee@example.com", "phone_number": "+919223344556"},
    {"username": "Srinivas Reddy", "email": "srinivas.reddy@example.com", "phone_number": "+919889900112"},
    {"username": "Aditi Verma", "email": "aditi.verma@example.com", "phone_number": "+919445566778"},
    {"username": "Rohit Kumar", "email": "rohit.kumar@example.com", "phone_number": "+919001122334"},
    {"username": "Kavitha Rao", "email": "kavitha.rao@example.com", "phone_number": "+919556644332"},
    {"username": "Debashish Patnaik", "email": "debashish.patnaik@example.com", "phone_number": "+919221100998"},
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
    print(f"Registering {len(USERS)} Indian users at {REGISTER_ENDPOINT}\n")
    seed()
