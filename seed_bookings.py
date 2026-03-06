"""
Seed script: create sample bookings via the API.

Usage:
    1. Make sure the backend server is running.
    2. Make sure users and listings have been seeded first.
    3. Set ACCESS_TOKEN below to a valid JWT access token (from any user).
    4. Run:  python seed_bookings.py

This script will:
    - Fetch all listings
    - Login as different users to create bookings
    - Create 2-3 bookings per listing with varied dates
"""

import json
import random
from datetime import date, timedelta

import requests

# ──────────────────────────────────────────────
#  CONFIG — edit these
# ──────────────────────────────────────────────
BASE_URL = "http://localhost:8000"
DEFAULT_PASSWORD = "Password123!"
# ──────────────────────────────────────────────

LOGIN_ENDPOINT = f"{BASE_URL}/api/v1/auth/login/"
LISTINGS_ENDPOINT = f"{BASE_URL}/api/v1/listings/"
BOOKINGS_ENDPOINT = f"{BASE_URL}/api/v1/bookings/"

# Indian users to book as (from seed_users.py)
GUEST_EMAILS = [
    "priya.sharma@example.com",
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


def login(email: str, password: str) -> dict | None:
    """Login and return tokens, or None on failure."""
    resp = requests.post(
        LOGIN_ENDPOINT,
        headers={"Content-Type": "application/json"},
        data=json.dumps({"email": email, "password": password}),
    )
    if resp.status_code == 200:
        return resp.json()
    return None


def get_listings(token: str) -> list:
    """Fetch all listings."""
    resp = requests.get(
        LISTINGS_ENDPOINT,
        headers={"Authorization": f"Bearer {token}"},
    )
    if resp.status_code == 200:
        data = resp.json()
        # Handle paginated response
        if isinstance(data, dict) and "results" in data:
            return data["results"]
        return data
    return []


def create_booking(token: str, listing_id: str, check_in: date, check_out: date, num_guests: int) -> dict | None:
    """Create a booking and return the response, or None on failure."""
    payload = {
        "listing_id": listing_id,
        "check_in": check_in.isoformat(),
        "check_out": check_out.isoformat(),
        "num_guests": num_guests,
        "special_requests": random.choice([
            "",
            "Early check-in if possible",
            "Late checkout requested",
            "Celebrating anniversary!",
            "Quiet room preferred",
            "Need extra towels",
            "Arriving late, around 10 PM",
            "Vegetarian meals only",
            "Prefer Indian breakfast",
        ]),
    }
    resp = requests.post(
        BOOKINGS_ENDPOINT,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        data=json.dumps(payload),
    )
    if resp.status_code == 201:
        return resp.json()
    return None


def generate_booking_dates(listing_index: int, booking_index: int) -> tuple[date, date]:
    """
    Generate check-in and check-out dates for a booking.
    Creates a mix of:
    - Past bookings (completed)
    - Current/ongoing bookings
    - Future bookings
    """
    today = date.today()
    
    # Patterns for different bookings
    patterns = [
        # Past bookings (30-60 days ago)
        (-60, -55, 3, 7),
        (-45, -40, 2, 5),
        (-30, -25, 4, 6),
        # Recent past (completed)
        (-20, -15, 2, 4),
        (-10, -5, 3, 5),
        # Future bookings
        (7, 14, 3, 7),
        (20, 30, 4, 8),
        (45, 60, 5, 10),
        (75, 90, 3, 6),
    ]
    
    # Pick a pattern based on listing and booking index
    pattern_index = (listing_index * 3 + booking_index) % len(patterns)
    start_offset_min, start_offset_max, duration_min, duration_max = patterns[pattern_index]
    
    # Add some randomness
    start_offset = random.randint(start_offset_min, start_offset_max)
    duration = random.randint(duration_min, duration_max)
    
    check_in = today + timedelta(days=start_offset)
    check_out = check_in + timedelta(days=duration)
    
    return check_in, check_out


def seed():
    print("=" * 60)
    print("BOOKING SEED SCRIPT")
    print("=" * 60)
    
    # Step 1: Login as first user to get listings
    print("\n[1/4] Logging in to fetch listings...")
    first_login = login(GUEST_EMAILS[0], DEFAULT_PASSWORD)
    if not first_login:
        print(f"  ERROR: Could not login as {GUEST_EMAILS[0]}")
        print("  Make sure seed_users.py has been run first.")
        return
    
    initial_token = first_login.get("access")
    print(f"  Logged in as {GUEST_EMAILS[0]}")
    
    # Step 2: Fetch all listings
    print("\n[2/4] Fetching all listings...")
    listings = get_listings(initial_token)
    if not listings:
        print("  ERROR: No listings found. Run seed_listings.py first.")
        return
    print(f"  Found {len(listings)} listings")
    
    # Step 3: Login as different users and collect tokens
    print("\n[3/4] Logging in as guest users...")
    user_tokens = {}
    user_ids = {}
    for email in GUEST_EMAILS:
        result = login(email, DEFAULT_PASSWORD)
        if result:
            user_tokens[email] = result.get("access")
            user_ids[email] = result.get("user", {}).get("id")
            print(f"  [OK] {email}")
        else:
            print(f"  [FAIL] {email}")
    
    if len(user_tokens) < 3:
        print("  ERROR: Need at least 3 users to create diverse bookings.")
        return
    
    # Step 4: Create bookings
    print("\n[4/4] Creating bookings...")
    print("-" * 60)
    
    created = 0
    failed = 0
    skipped = 0
    
    available_guests = list(user_tokens.keys())
    
    for listing_idx, listing in enumerate(listings):
        listing_id = listing["id"]
        listing_title = listing["title"][:40]
        host_id = listing.get("host", {}).get("id")
        
        # Create 2-3 bookings per listing
        num_bookings = random.randint(2, 3)
        
        # Shuffle guests and pick ones that aren't the host
        random.shuffle(available_guests)
        valid_guests = [g for g in available_guests if user_ids.get(g) != host_id]
        
        for booking_idx in range(num_bookings):
            if booking_idx >= len(valid_guests):
                print(f"  [{listing_idx+1}.{booking_idx+1}] SKIP: Not enough guests for {listing_title}")
                skipped += 1
                continue
            
            guest_email = valid_guests[booking_idx]
            token = user_tokens[guest_email]
            
            # Generate dates
            check_in, check_out = generate_booking_dates(listing_idx, booking_idx)
            
            # Random number of guests (1 to max_guests)
            max_guests = listing.get("max_guests", 4)
            num_guests = random.randint(1, min(max_guests, 6))
            
            # Create booking
            result = create_booking(
                token=token,
                listing_id=listing_id,
                check_in=check_in,
                check_out=check_out,
                num_guests=num_guests,
            )
            
            if result:
                booking_data = result.get("booking", {})
                total_price = booking_data.get("total_price")
                
                print(
                    f"  [{listing_idx+1}.{booking_idx+1}] OK: {listing_title[:30]}... "
                    f"Guest: {guest_email.split('@')[0]}, "
                    f"Dates: {check_in} -> {check_out}, "
                    f"₹{total_price} [PENDING]"
                )
                created += 1
            else:
                print(
                    f"  [{listing_idx+1}.{booking_idx+1}] FAILED: {listing_title[:30]}... "
                    f"({check_in} -> {check_out})"
                )
                failed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Total listings:     {len(listings)}")
    print(f"  Bookings created:   {created} (all pending payment)")
    print(f"  Failed:             {failed}")
    print("=" * 60)


if __name__ == "__main__":
    seed()
