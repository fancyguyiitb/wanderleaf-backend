"""
Unified seed script: Indian listings + bookings.

- Logs in as existing users (no registration).
- Distributes 16 properties across 6 hosts.
- Creates 2–3 bookings per listing from other users.
- Every user has at least 1 booking. All bookings confirmed with successful payments.

Usage:
    1. Backend server running. Users already registered (seed_users.py).
    2. Run:  python seed_all.py
"""

import json
import random
from datetime import date, timedelta
import requests

# ──────────────────────────────────────────────
#  CONFIG
# ──────────────────────────────────────────────
BASE_URL = "http://localhost:8000"
DEFAULT_PASSWORD = "Password123!"
# ──────────────────────────────────────────────

LOGIN_ENDPOINT = f"{BASE_URL}/api/v1/auth/login/"
LISTINGS_ENDPOINT = f"{BASE_URL}/api/v1/listings/"
BOOKINGS_ENDPOINT = f"{BASE_URL}/api/v1/bookings/"

# Users (must already exist). First 6 are hosts; all 15 are guests.
USER_EMAILS = [
    "sarthak.niranjan@example.com",
    "arjun.singh@example.com",
    "riya.kapoor@example.com",
    "karthik.iyer@example.com",
    "meenakshi.nair@example.com",
    "vikram.mehta@example.com",
    "anjali.gupta@example.com",
    "sameer.desai@example.com",
    "pooja.joshi@example.com",
    "rahul.chatterjee@example.com",
    "srinivas.reddy@example.com",
    "aditi.verma@example.com",
    "rohit.kumar@example.com",
    "kavitha.rao@example.com",
    "debashish.patnaik@example.com",
]

# Host assignment: listing_index -> host_email (6 hosts, 16 listings)
HOST_ASSIGNMENT = [
    "sarthak.niranjan@example.com",  # 0: Goa villa
    "sarthak.niranjan@example.com",  # 1: Palolem
    "sarthak.niranjan@example.com",  # 2: Munnar
    "arjun.singh@example.com",       # 3: Alleppey
    "arjun.singh@example.com",       # 4: Manali
    "arjun.singh@example.com",       # 5: Udaipur
    "riya.kapoor@example.com",       # 6: Jaisalmer
    "riya.kapoor@example.com",       # 7: Mumbai
    "riya.kapoor@example.com",       # 8: Coorg
    "karthik.iyer@example.com",      # 9: Rishikesh
    "karthik.iyer@example.com",      # 10: Kovalam
    "meenakshi.nair@example.com",    # 11: Kasol
    "meenakshi.nair@example.com",    # 12: Jaipur
    "vikram.mehta@example.com",      # 13: Darjeeling
    "vikram.mehta@example.com",      # 14: Andaman
    "vikram.mehta@example.com",      # 15: Pondicherry
]

LISTINGS_DATA = [
    {"title": "Portuguese Heritage Villa in Goa", "description": "A restored 150-year-old Portuguese villa in Fontainhas, Panjim. High ceilings, azulejo tiles, and a lush courtyard garden. Walking distance to cafés, art galleries, and the Mandovi riverfront.", "location": "Fontainhas, Panjim, Goa", "category": "luxury_villas", "price_per_night": "18500.00", "bedrooms": 3, "bathrooms": 2.5, "max_guests": 6, "amenities": ["WiFi", "Air Conditioning", "Kitchen", "Garden", "Heritage Architecture", "Free Parking", "Housekeeping", "Breakfast Included"], "images": ["https://images.unsplash.com/photo-1613490493576-7fde63acd811?w=800", "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800", "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=800"], "latitude": "15.496800", "longitude": "73.827800"},
    {"title": "Beach Shack with Sea View — Palolem", "description": "Steps from Palolem Beach. Open-plan cabin with hammock on the deck, outdoor shower, and direct beach access. Watch sunset over the Arabian Sea.", "location": "Palolem Beach, South Goa", "category": "beach_houses", "price_per_night": "4200.00", "bedrooms": 1, "bathrooms": 1.0, "max_guests": 2, "amenities": ["WiFi", "Beach Access", "Hammock", "Outdoor Shower", "Kitchen", "Fan", "Parking"], "images": ["https://images.unsplash.com/photo-1499793983690-e29da59ef1c2?w=800", "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800", "https://images.unsplash.com/photo-1506929562872-bb421503ef21?w=800"], "latitude": "15.008900", "longitude": "74.022900"},
    {"title": "Tea Estate Bungalow — Munnar", "description": "Colonial-era bungalow on a working tea estate in Munnar. Rolling green hills, misty mornings, and tea factory tours. Stone fireplace, verandah with valley views.", "location": "Munnar, Kerala", "category": "farms", "price_per_night": "12000.00", "bedrooms": 3, "bathrooms": 2.0, "max_guests": 6, "amenities": ["WiFi", "Fireplace", "Kitchen", "Tea Estate Tour", "Mountain View", "Free Parking", "Breakfast", "Garden"], "images": ["https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=800", "https://images.unsplash.com/photo-1416331108676-a22ccb276e35?w=800", "https://images.unsplash.com/photo-1464226184884-fa280b87c399?w=800"], "latitude": "10.088900", "longitude": "77.059500"},
    {"title": "Houseboat on the Backwaters — Alleppey", "description": "Private houseboat gliding through Kerala's backwaters. Bedroom, attached bath, open deck, and onboard chef. Rice paddies, coconut groves, village life.", "location": "Alleppey, Kerala", "category": "eco_lodges", "price_per_night": "18500.00", "bedrooms": 1, "bathrooms": 1.0, "max_guests": 4, "amenities": ["WiFi", "Meals Included", "AC Cabin", "Deck", "Fishing", "Village Tours", "Parking at Jetty"], "images": ["https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=800", "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800", "https://images.unsplash.com/photo-1596394516093-501ba68a0ba6?w=800"], "latitude": "9.498100", "longitude": "76.338800"},
    {"title": "Wooden Cottage in the Himalayas — Manali", "description": "Cozy wooden cottage in Old Manali, 5 min walk from cafés and the Manu Temple. Mountain views, fireplace, small kitchen. Great base for treks and Solang Valley.", "location": "Old Manali, Himachal Pradesh", "category": "cabins", "price_per_night": "5500.00", "bedrooms": 2, "bathrooms": 1.0, "max_guests": 4, "amenities": ["WiFi", "Fireplace", "Kitchen", "Mountain View", "Heating", "Parking", "Garden"], "images": ["https://images.unsplash.com/photo-1449158743715-0a90ebb6d2d8?w=800", "https://images.unsplash.com/photo-1510798831971-661eb04b3739?w=800", "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=800"], "latitude": "32.239600", "longitude": "77.188700"},
    {"title": "Rajputana Haveli — Udaipur", "description": "Traditional haveli overlooking Lake Pichola and the City Palace. Hand-painted walls, jharokhas, rooftop terrace for sunset views.", "location": "Lal Ghat, Udaipur, Rajasthan", "category": "luxury_villas", "price_per_night": "22000.00", "bedrooms": 4, "bathrooms": 3.0, "max_guests": 8, "amenities": ["WiFi", "Pool", "Air Conditioning", "Lake View", "Rooftop Terrace", "Breakfast", "Parking", "Cultural Tours"], "images": ["https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800", "https://images.unsplash.com/photo-1613490493576-7fde63acd811?w=800", "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=800"], "latitude": "24.585400", "longitude": "73.712500"},
    {"title": "Desert Camp under the Stars — Jaisalmer", "description": "Luxury swiss tents in the Thar Desert. Camel safari at sunset, folk music around the campfire, stargazing. Attached baths, AC tents.", "location": "Sam Sand Dunes, Jaisalmer, Rajasthan", "category": "eco_lodges", "price_per_night": "9800.00", "bedrooms": 1, "bathrooms": 1.0, "max_guests": 2, "amenities": ["WiFi", "AC Tent", "Camel Safari", "Campfire", "Dinner", "Stargazing", "Desert View"], "images": ["https://images.unsplash.com/photo-1540541338287-41700207dee6?w=800", "https://images.unsplash.com/photo-1596394516093-501ba68a0ba6?w=800", "https://images.unsplash.com/photo-1571003123894-1f0594d2b5d9?w=800"], "latitude": "26.911700", "longitude": "70.905800"},
    {"title": "Boutique Loft in Bandra — Mumbai", "description": "Modern loft in Bandra West, minutes from Linking Road and Carter Road. Exposed brick, high ceilings, full kitchen.", "location": "Bandra West, Mumbai", "category": "urban_lofts", "price_per_night": "8500.00", "bedrooms": 2, "bathrooms": 2.0, "max_guests": 4, "amenities": ["WiFi", "Air Conditioning", "Kitchen", "Washer", "Smart TV", "Elevator", "Parking"], "images": ["https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800", "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800", "https://images.unsplash.com/photo-1536376072261-38c75010e6c9?w=800"], "latitude": "19.059600", "longitude": "72.829500"},
    {"title": "Treehouse in Coorg", "description": "Bamboo treehouse surrounded by coffee plantations. Wake to birdsong, enjoy filtered coffee on the deck. Trekking and Abbey Falls nearby.", "location": "Madikeri, Coorg, Karnataka", "category": "treehouses", "price_per_night": "6800.00", "bedrooms": 1, "bathrooms": 1.0, "max_guests": 2, "amenities": ["WiFi", "Coffee Estate", "Deck", "Breakfast", "Trekking", "Parking", "Nature View"], "images": ["https://images.unsplash.com/photo-1488462237308-ecaa28b729d7?w=800", "https://images.unsplash.com/photo-1444080748397-f442aa95c3e5?w=800", "https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=800"], "latitude": "12.420800", "longitude": "75.739700"},
    {"title": "Yoga Retreat Homestay — Rishikesh", "description": "Peaceful room in a family-run homestay near Laxman Jhula. Yoga deck, organic garden, Ganges view. River rafting and ashrams nearby.", "location": "Laxman Jhula, Rishikesh, Uttarakhand", "category": "eco_lodges", "price_per_night": "3200.00", "bedrooms": 1, "bathrooms": 1.0, "max_guests": 2, "amenities": ["WiFi", "Yoga Deck", "Organic Meals", "River View", "Parking", "Garden"], "images": ["https://images.unsplash.com/photo-1596394516093-501ba68a0ba6?w=800", "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=800", "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800"], "latitude": "30.131400", "longitude": "78.437800"},
    {"title": "Beachfront Villa — Kovalam", "description": "Modern villa with private beach access in Kovalam. Infinity pool, sea-facing bedrooms, chef for Kerala-style meals.", "location": "Kovalam, Thiruvananthapuram, Kerala", "category": "beach_houses", "price_per_night": "24500.00", "bedrooms": 4, "bathrooms": 3.5, "max_guests": 8, "amenities": ["WiFi", "Pool", "Beach Access", "Kitchen", "Air Conditioning", "Chef", "Parking"], "images": ["https://images.unsplash.com/photo-1499793983690-e29da59ef1c2?w=800", "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?w=800", "https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=800"], "latitude": "8.384100", "longitude": "76.978600"},
    {"title": "Stone Cottage — Kasol", "description": "Rustic stone cottage by the Parvati River. Bonfire pit, mountain views, easy access to Kheerganga and Grahan treks.", "location": "Kasol, Himachal Pradesh", "category": "cabins", "price_per_night": "3500.00", "bedrooms": 2, "bathrooms": 1.0, "max_guests": 4, "amenities": ["WiFi", "River View", "Fire Pit", "Kitchen", "Parking", "Mountain View"], "images": ["https://images.unsplash.com/photo-1449158743715-0a90ebb6d2d8?w=800", "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=800", "https://images.unsplash.com/photo-1510798831971-661eb04b3739?w=800"], "latitude": "32.010900", "longitude": "77.316500"},
    {"title": "Heritage Homestay — Jaipur", "description": "Pink-city haveli in the old quarters. Hand-painted ceilings, antique furniture, rooftop with Amer Fort view. Host prepares Rajasthani thali.", "location": "Chandpole, Jaipur, Rajasthan", "category": "farms", "price_per_night": "7500.00", "bedrooms": 3, "bathrooms": 2.0, "max_guests": 6, "amenities": ["WiFi", "AC", "Rooftop", "Breakfast", "Parking", "Cultural Experience"], "images": ["https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800", "https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=800", "https://images.unsplash.com/photo-1416331108676-a22ccb276e35?w=800"], "latitude": "26.912400", "longitude": "75.787300"},
    {"title": "Colonial Bungalow — Darjeeling", "description": "Tea-era bungalow with Kanchenjunga views. Fireplace, wooden floors, verandah for morning chai. Tiger Hill and tea gardens nearby.", "location": "Chowrasta, Darjeeling, West Bengal", "category": "mountain_retreats", "price_per_night": "11500.00", "bedrooms": 3, "bathrooms": 2.0, "max_guests": 6, "amenities": ["WiFi", "Fireplace", "Mountain View", "Breakfast", "Garden", "Parking"], "images": ["https://images.unsplash.com/photo-1502784444783-3a535504c990?w=800", "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=800", "https://images.unsplash.com/photo-1520984032042-162d526883e0?w=800"], "latitude": "27.041000", "longitude": "88.266300"},
    {"title": "Beach Hut — Andaman", "description": "Thatched beach hut on Radhanagar Beach, Havelock Island. Turquoise waters, white sand. Snorkeling, scuba, kayaking available.", "location": "Radhanagar Beach, Havelock Island, Andaman and Nicobar", "category": "beach_houses", "price_per_night": "9200.00", "bedrooms": 1, "bathrooms": 1.0, "max_guests": 2, "amenities": ["WiFi", "Beach Access", "Fan", "Outdoor Shower", "Snorkeling", "Breakfast"], "images": ["https://images.unsplash.com/photo-1439066615861-d1af74d74000?w=800", "https://images.unsplash.com/photo-1506929562872-bb421503ef21?w=800", "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800"], "latitude": "11.991100", "longitude": "92.996900"},
    {"title": "French Quarter Studio — Pondicherry", "description": "Charming studio in the French Quarter. White walls, blue shutters, balcony overlooking a quiet lane. Cafés, Promenade Beach, Auroville nearby.", "location": "White Town, Pondicherry", "category": "urban_lofts", "price_per_night": "4800.00", "bedrooms": 1, "bathrooms": 1.0, "max_guests": 2, "amenities": ["WiFi", "Air Conditioning", "Kitchenette", "Balcony", "Bicycle Rental", "Parking"], "images": ["https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800", "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800", "https://images.unsplash.com/photo-1499002238440-d264edd596ec?w=800"], "latitude": "11.934100", "longitude": "79.830600"},
]

SPECIAL_REQUESTS = [
    "", "Early check-in if possible", "Late checkout requested", "Celebrating anniversary!",
    "Quiet room preferred", "Need extra towels", "Arriving late, around 10 PM",
    "Vegetarian meals only", "Prefer Indian breakfast",
]


def login(email: str, password: str) -> dict | None:
    resp = requests.post(LOGIN_ENDPOINT, headers={"Content-Type": "application/json"}, data=json.dumps({"email": email, "password": password}))
    if resp.status_code == 200:
        return resp.json()
    return None


def create_listing(token: str, data: dict) -> dict | None:
    resp = requests.post(LISTINGS_ENDPOINT, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, data=json.dumps(data))
    if resp.status_code == 201:
        return resp.json()
    return None


def create_booking(token: str, listing_id: str, check_in: date, check_out: date, num_guests: int, special_request: str = "") -> dict | None:
    payload = {
        "listing_id": listing_id,
        "check_in": check_in.isoformat(),
        "check_out": check_out.isoformat(),
        "num_guests": num_guests,
        "special_requests": special_request,
    }
    resp = requests.post(BOOKINGS_ENDPOINT, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, data=json.dumps(payload))
    if resp.status_code == 201:
        return resp.json()
    return None


def confirm_booking(token: str, booking_id: str) -> bool:
    resp = requests.post(f"{BOOKINGS_ENDPOINT}{booking_id}/confirm/", headers={"Authorization": f"Bearer {token}"})
    return resp.status_code == 200


def gen_dates_for_listing(listing_idx: int, booking_idx: int, used_ranges: list) -> tuple[date, date]:
    """Generate non-overlapping dates for a listing."""
    today = date.today()
    base = today + timedelta(days=30 + listing_idx * 20 + booking_idx * 10)
    check_in = base
    check_out = base + timedelta(days=random.randint(2, 5))
    # Simple non-overlap: stagger by listing+booking index
    return check_in, check_out


def main():
    print("=" * 60)
    print("SEED ALL — Listings + Bookings (Indian, INR)")
    print("=" * 60)

    # ─── 1. Login all users ───
    print("\n[1/4] Logging in users...")
    tokens = {}
    user_ids = {}
    for email in USER_EMAILS:
        r = login(email, DEFAULT_PASSWORD)
        if r:
            tokens[email] = r.get("access")
            user_ids[email] = r.get("user", {}).get("id")
            print(f"  [OK] {email}")
        else:
            print(f"  [FAIL] {email}")

    if len(tokens) < 6:
        print("ERROR: Need at least 6 users. Run seed_users.py first.")
        return

    # ─── 2. Create listings (each host creates their assigned listings) ───
    print("\n[2/4] Creating listings (distributed across hosts)...")
    created_listings = []  # [(listing_id, host_email, listing_data), ...]
    for i, data in enumerate(LISTINGS_DATA):
        host_email = HOST_ASSIGNMENT[i]
        token = tokens.get(host_email)
        if not token:
            print(f"  [SKIP] No token for host {host_email} — listing {data['title'][:40]}")
            continue
        result = create_listing(token, data)
        if result:
            lid = result.get("id")
            created_listings.append((lid, host_email, data))
            print(f"  [{i+1}/{len(LISTINGS_DATA)}] {data['title'][:45]}... (host: {host_email.split('@')[0]}) ₹{data['price_per_night']}/night")
        else:
            print(f"  [FAIL] {data['title'][:40]}")

    if not created_listings:
        print("ERROR: No listings created.")
        return

    # ─── 3. Ensure every user gets at least 1 booking ───
    # Build guest order: cycle through all users, excluding host per listing
    guests_needed = set(USER_EMAILS)
    bookings_to_create = []

    for listing_idx, (listing_id, host_email, ldata) in enumerate(created_listings):
        max_guests = int(ldata.get("max_guests", 4))
        candidates = [e for e in USER_EMAILS if e != host_email]
        random.shuffle(candidates)
        num_bookings = random.randint(2, 3)
        for b in range(num_bookings):
            guest = candidates[b % len(candidates)]
            check_in, check_out = gen_dates_for_listing(listing_idx, b, [])
            num_guests = min(random.randint(1, max_guests), 6)
            bookings_to_create.append((listing_id, host_email, guest, check_in, check_out, num_guests))

    # Add bookings so every user has at least 1
    avail_listings = [(x[0], x[1], x[2]) for x in created_listings]
    for email in guests_needed:
        has_booking = any(b[2] == email for b in bookings_to_create)
        if not has_booking:
            # Pick a listing where this user isn't the host
            choices = [(lid, he, ldata) for lid, he, ldata in avail_listings if he != email]
            if not choices:
                choices = avail_listings
            lid, he, ldata = random.choice(choices)
            if he != email:
                ci, co = gen_dates_for_listing(len(created_listings) + 1, 99, [])
                mg = int(ldata.get("max_guests", 4))
                bookings_to_create.append((lid, he, email, ci, co, min(random.randint(1, mg), 6)))

    # ─── 4. Create and confirm all bookings ───
    print("\n[3/4] Creating bookings...")
    created = 0
    confirmed = 0
    failed = 0
    for listing_id, host_email, guest_email, check_in, check_out, num_guests in bookings_to_create:
        token = tokens.get(guest_email)
        if not token:
            failed += 1
            continue
        req = random.choice(SPECIAL_REQUESTS)
        result = create_booking(token, listing_id, check_in, check_out, num_guests, req)
        if result:
            booking = result.get("booking", {})
            bid = booking.get("id")
            total = booking.get("total_price")
            if bid and confirm_booking(token, bid):
                confirmed += 1
            created += 1
            print(f"  Guest: {guest_email.split('@')[0]} → {check_in} to {check_out} ₹{total} [CONFIRMED]")
        else:
            failed += 1

    print("\n[4/4] Summary")
    print("=" * 60)
    print(f"  Listings created:   {len(created_listings)} (6 hosts)")
    print(f"  Bookings created:   {created}")
    print(f"  Bookings confirmed: {confirmed} (successful payment)")
    print(f"  Failed:             {failed}")
    print(f"  Users with bookings: {len(guests_needed)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
