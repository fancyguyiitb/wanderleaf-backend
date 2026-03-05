"""
Seed script: create Indian property listings via the API.

All prices are in INR. Locations across India.

Usage:
    1. Run seed_users.py first. Login as any user to get ACCESS_TOKEN.
    2. Set ACCESS_TOKEN below to a valid JWT access token.
    3. Run:  python seed_listings.py
"""

import json
import requests

# ──────────────────────────────────────────────
#  CONFIG — edit these
# ──────────────────────────────────────────────
ACCESS_TOKEN = ""
BASE_URL = "http://localhost:8000"
# ──────────────────────────────────────────────

ENDPOINT = f"{BASE_URL}/api/v1/listings/"

HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json",
}

# Indian properties — prices in INR
LISTINGS = [
    {
        "title": "Portuguese Heritage Villa in Goa",
        "description": "A restored 150-year-old Portuguese villa in Fontainhas, Panjim. High ceilings, azulejo tiles, and a lush courtyard garden. Walking distance to cafés, art galleries, and the Mandovi riverfront. Perfect for couples or small groups exploring Goa's heritage quarter.",
        "location": "Fontainhas, Panjim, Goa",
        "category": "luxury_villas",
        "price_per_night": "18500.00",
        "bedrooms": 3,
        "bathrooms": 2.5,
        "max_guests": 6,
        "amenities": ["WiFi", "Air Conditioning", "Kitchen", "Garden", "Heritage Architecture", "Free Parking", "Housekeeping", "Breakfast Included"],
        "images": [
            "https://images.unsplash.com/photo-1613490493576-7fde63acd811?w=800",
            "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800",
            "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=800",
        ],
        "latitude": "15.496800",
        "longitude": "73.827800",
    },
    {
        "title": "Beach Shack with Sea View — Palolem",
        "description": "Steps from Palolem Beach. Open-plan cabin with hammock on the deck, outdoor shower, and direct beach access. Watch sunset over the Arabian Sea. Popular cafés and water sports nearby.",
        "location": "Palolem Beach, South Goa",
        "category": "beach_houses",
        "price_per_night": "4200.00",
        "bedrooms": 1,
        "bathrooms": 1.0,
        "max_guests": 2,
        "amenities": ["WiFi", "Beach Access", "Hammock", "Outdoor Shower", "Kitchen", "Fan", "Parking"],
        "images": [
            "https://images.unsplash.com/photo-1499793983690-e29da59ef1c2?w=800",
            "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800",
            "https://images.unsplash.com/photo-1506929562872-bb421503ef21?w=800",
        ],
        "latitude": "15.008900",
        "longitude": "74.022900",
    },
    {
        "title": "Tea Estate Bungalow — Munnar",
        "description": "Colonial-era bungalow on a working tea estate in Munnar. Rolling green hills, misty mornings, and tea factory tours. Stone fireplace, verandah with valley views. Ideal for nature lovers and families.",
        "location": "Munnar, Kerala",
        "category": "farms",
        "price_per_night": "12000.00",
        "bedrooms": 3,
        "bathrooms": 2.0,
        "max_guests": 6,
        "amenities": ["WiFi", "Fireplace", "Kitchen", "Tea Estate Tour", "Mountain View", "Free Parking", "Breakfast", "Garden"],
        "images": [
            "https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=800",
            "https://images.unsplash.com/photo-1416331108676-a22ccb276e35?w=800",
            "https://images.unsplash.com/photo-1464226184884-fa280b87c399?w=800",
        ],
        "latitude": "10.088900",
        "longitude": "77.059500",
    },
    {
        "title": "Houseboat on the Backwaters — Alleppey",
        "description": "Private houseboat gliding through Kerala's backwaters. Bedroom, attached bath, open deck, and onboard chef. Rice paddies, coconut groves, and village life glide past. Full-board meals included.",
        "location": "Alleppey, Kerala",
        "category": "eco_lodges",
        "price_per_night": "18500.00",
        "bedrooms": 1,
        "bathrooms": 1.0,
        "max_guests": 4,
        "amenities": ["WiFi", "Meals Included", "AC Cabin", "Deck", "Fishing", "Village Tours", "Parking at Jetty"],
        "images": [
            "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=800",
            "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800",
            "https://images.unsplash.com/photo-1596394516093-501ba68a0ba6?w=800",
        ],
        "latitude": "9.498100",
        "longitude": "76.338800",
    },
    {
        "title": "Wooden Cottage in the Himalayas — Manali",
        "description": "Cozy wooden cottage in Old Manali, 5 min walk from cafés and the Manu Temple. Mountain views, fireplace, and a small kitchen. Great base for treks, paragliding, and Solang Valley.",
        "location": "Old Manali, Himachal Pradesh",
        "category": "cabins",
        "price_per_night": "5500.00",
        "bedrooms": 2,
        "bathrooms": 1.0,
        "max_guests": 4,
        "amenities": ["WiFi", "Fireplace", "Kitchen", "Mountain View", "Heating", "Parking", "Garden"],
        "images": [
            "https://images.unsplash.com/photo-1449158743715-0a90ebb6d2d8?w=800",
            "https://images.unsplash.com/photo-1510798831971-661eb04b3739?w=800",
            "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=800",
        ],
        "latitude": "32.239600",
        "longitude": "77.188700",
    },
    {
        "title": "Rajputana Haveli — Udaipur",
        "description": "Traditional haveli overlooking Lake Pichola and the City Palace. Hand-painted walls, jharokhas, and a rooftop terrace for sunset views. Rickshaw to the old city in minutes.",
        "location": "Lal Ghat, Udaipur, Rajasthan",
        "category": "luxury_villas",
        "price_per_night": "22000.00",
        "bedrooms": 4,
        "bathrooms": 3.0,
        "max_guests": 8,
        "amenities": ["WiFi", "Pool", "Air Conditioning", "Lake View", "Rooftop Terrace", "Breakfast", "Parking", "Cultural Tours"],
        "images": [
            "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800",
            "https://images.unsplash.com/photo-1613490493576-7fde63acd811?w=800",
            "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=800",
        ],
        "latitude": "24.585400",
        "longitude": "73.712500",
    },
    {
        "title": "Desert Camp under the Stars — Jaisalmer",
        "description": "Luxury swiss tents in the Thar Desert. Camel safari at sunset, folk music around the campfire, and stargazing. Attached baths, AC tents. Wake to dunes and silence.",
        "location": "Sam Sand Dunes, Jaisalmer, Rajasthan",
        "category": "eco_lodges",
        "price_per_night": "9800.00",
        "bedrooms": 1,
        "bathrooms": 1.0,
        "max_guests": 2,
        "amenities": ["WiFi", "AC Tent", "Camel Safari", "Campfire", "Dinner", "Stargazing", "Desert View"],
        "images": [
            "https://images.unsplash.com/photo-1540541338287-41700207dee6?w=800",
            "https://images.unsplash.com/photo-1596394516093-501ba68a0ba6?w=800",
            "https://images.unsplash.com/photo-1571003123894-1f0594d2b5d9?w=800",
        ],
        "latitude": "26.911700",
        "longitude": "70.905800",
    },
    {
        "title": "Boutique Loft in Bandra — Mumbai",
        "description": "Modern loft in Bandra West, minutes from Linking Road and Carter Road. Exposed brick, high ceilings, full kitchen. Ideal for workcations or exploring Mumbai's cafés and nightlife.",
        "location": "Bandra West, Mumbai",
        "category": "urban_lofts",
        "price_per_night": "8500.00",
        "bedrooms": 2,
        "bathrooms": 2.0,
        "max_guests": 4,
        "amenities": ["WiFi", "Air Conditioning", "Kitchen", "Washer", "Smart TV", "Elevator", "Parking"],
        "images": [
            "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800",
            "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800",
            "https://images.unsplash.com/photo-1536376072261-38c75010e6c9?w=800",
        ],
        "latitude": "19.059600",
        "longitude": "72.829500",
    },
    {
        "title": "Treehouse in Coorg",
        "description": "Bamboo treehouse surrounded by coffee plantations. Wake to birdsong, enjoy filtered coffee on the deck. Trekking, river rafting, and Abbey Falls nearby.",
        "location": "Madikeri, Coorg, Karnataka",
        "category": "treehouses",
        "price_per_night": "6800.00",
        "bedrooms": 1,
        "bathrooms": 1.0,
        "max_guests": 2,
        "amenities": ["WiFi", "Coffee Estate", "Deck", "Breakfast", "Trekking", "Parking", "Nature View"],
        "images": [
            "https://images.unsplash.com/photo-1488462237308-ecaa28b729d7?w=800",
            "https://images.unsplash.com/photo-1444080748397-f442aa95c3e5?w=800",
            "https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=800",
        ],
        "latitude": "12.420800",
        "longitude": "75.739700",
    },
    {
        "title": "Yoga Retreat Homestay — Rishikesh",
        "description": "Peaceful room in a family-run homestay near Laxman Jhula. Yoga deck, organic garden, and Ganges view. Perfect for yoga, meditation, or a quiet escape. River rafting and ashrams nearby.",
        "location": "Laxman Jhula, Rishikesh, Uttarakhand",
        "category": "eco_lodges",
        "price_per_night": "3200.00",
        "bedrooms": 1,
        "bathrooms": 1.0,
        "max_guests": 2,
        "amenities": ["WiFi", "Yoga Deck", "Organic Meals", "River View", "Parking", "Garden"],
        "images": [
            "https://images.unsplash.com/photo-1596394516093-501ba68a0ba6?w=800",
            "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=800",
            "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800",
        ],
        "latitude": "30.131400",
        "longitude": "78.437800",
    },
    {
        "title": "Beachfront Villa — Kovalam",
        "description": "Modern villa with private beach access in Kovalam. Infinity pool, sea-facing bedrooms, and a chef for Kerala-style meals. Lighthouse Beach and Hawah Beach within walking distance.",
        "location": "Kovalam, Thiruvananthapuram, Kerala",
        "category": "beach_houses",
        "price_per_night": "24500.00",
        "bedrooms": 4,
        "bathrooms": 3.5,
        "max_guests": 8,
        "amenities": ["WiFi", "Pool", "Beach Access", "Kitchen", "Air Conditioning", "Chef", "Parking"],
        "images": [
            "https://images.unsplash.com/photo-1499793983690-e29da59ef1c2?w=800",
            "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?w=800",
            "https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=800",
        ],
        "latitude": "8.384100",
        "longitude": "76.978600",
    },
    {
        "title": "Stone Cottage — Kasol",
        "description": "Rustic stone cottage by the Parvati River. Bonfire pit, mountain views, and easy access to treks (Kheerganga, Grahan). Cafés and Israeli food a short walk away.",
        "location": "Kasol, Himachal Pradesh",
        "category": "cabins",
        "price_per_night": "3500.00",
        "bedrooms": 2,
        "bathrooms": 1.0,
        "max_guests": 4,
        "amenities": ["WiFi", "River View", "Fire Pit", "Kitchen", "Parking", "Mountain View"],
        "images": [
            "https://images.unsplash.com/photo-1449158743715-0a90ebb6d2d8?w=800",
            "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=800",
            "https://images.unsplash.com/photo-1510798831971-661eb04b3739?w=800",
        ],
        "latitude": "32.010900",
        "longitude": "77.316500",
    },
    {
        "title": "Heritage Homestay — Jaipur",
        "description": "Pink-city haveli in the old quarters. Hand-painted ceilings, antique furniture, and a rooftop with Amer Fort view. Host prepares Rajasthani thali. Walking distance to markets and Hawa Mahal.",
        "location": "Chandpole, Jaipur, Rajasthan",
        "category": "farms",
        "price_per_night": "7500.00",
        "bedrooms": 3,
        "bathrooms": 2.0,
        "max_guests": 6,
        "amenities": ["WiFi", "AC", "Rooftop", "Breakfast", "Parking", "Cultural Experience"],
        "images": [
            "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800",
            "https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=800",
            "https://images.unsplash.com/photo-1416331108676-a22ccb276e35?w=800",
        ],
        "latitude": "26.912400",
        "longitude": "75.787300",
    },
    {
        "title": "Colonial Bungalow — Darjeeling",
        "description": "Tea-era bungalow with Kanchenjunga views. Fireplace, wooden floors, and a verandah for morning chai. Tiger Hill, Batasia Loop, and tea gardens nearby.",
        "location": "Chowrasta, Darjeeling, West Bengal",
        "category": "mountain_retreats",
        "price_per_night": "11500.00",
        "bedrooms": 3,
        "bathrooms": 2.0,
        "max_guests": 6,
        "amenities": ["WiFi", "Fireplace", "Mountain View", "Breakfast", "Garden", "Parking"],
        "images": [
            "https://images.unsplash.com/photo-1502784444783-3a535504c990?w=800",
            "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=800",
            "https://images.unsplash.com/photo-1520984032042-162d526883e0?w=800",
        ],
        "latitude": "27.041000",
        "longitude": "88.266300",
    },
    {
        "title": "Beach Hut — Andaman",
        "description": "Thatched beach hut on Radhanagar Beach, Havelock Island. Wake to turquoise waters and white sand. Snorkeling, scuba, and kayaking available. Minimalist, eco-friendly setup.",
        "location": "Radhanagar Beach, Havelock Island, Andaman and Nicobar",
        "category": "beach_houses",
        "price_per_night": "9200.00",
        "bedrooms": 1,
        "bathrooms": 1.0,
        "max_guests": 2,
        "amenities": ["WiFi", "Beach Access", "Fan", "Outdoor Shower", "Snorkeling", "Breakfast"],
        "images": [
            "https://images.unsplash.com/photo-1439066615861-d1af74d74000?w=800",
            "https://images.unsplash.com/photo-1506929562872-bb421503ef21?w=800",
            "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800",
        ],
        "latitude": "11.991100",
        "longitude": "92.996900",
    },
    {
        "title": "French Quarter Studio — Pondicherry",
        "description": "Charming studio in the French Quarter. White walls, blue shutters, and a balcony overlooking a quiet lane. Cafés, Promenade Beach, and Auroville within easy reach.",
        "location": "White Town, Pondicherry",
        "category": "urban_lofts",
        "price_per_night": "4800.00",
        "bedrooms": 1,
        "bathrooms": 1.0,
        "max_guests": 2,
        "amenities": ["WiFi", "Air Conditioning", "Kitchenette", "Balcony", "Bicycle Rental", "Parking"],
        "images": [
            "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800",
            "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800",
            "https://images.unsplash.com/photo-1499002238440-d264edd596ec?w=800",
        ],
        "latitude": "11.934100",
        "longitude": "79.830600",
    },
]


def seed():
    created = 0
    failed = 0

    for i, listing in enumerate(LISTINGS, 1):
        resp = requests.post(ENDPOINT, headers=HEADERS, data=json.dumps(listing))

        if resp.status_code == 201:
            data = resp.json()
            print(f"  [{i}/{len(LISTINGS)}] Created: {data['title']}  (id: {data['id']}) ₹{listing['price_per_night']}/night")
            created += 1
        else:
            print(f"  [{i}/{len(LISTINGS)}] FAILED: {listing['title']}")
            print(f"           Status {resp.status_code}: {resp.text[:200]}")
            failed += 1

    print(f"\nDone — {created} created, {failed} failed. (All prices in INR)")


if __name__ == "__main__":
    if ACCESS_TOKEN == "PASTE_YOUR_ACCESS_TOKEN_HERE":
        print("ERROR: Set your ACCESS_TOKEN at the top of this script first.")
        print("       Run seed_users.py, login as any user, and paste the JWT access token.")
        raise SystemExit(1)

    print(f"Seeding {len(LISTINGS)} Indian listings (INR) to {ENDPOINT}\n")
    seed()
