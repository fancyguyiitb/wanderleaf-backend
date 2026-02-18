"""
Seed script: create sample property listings via the API.

Usage:
    1. Set ACCESS_TOKEN below to a valid JWT access token.
    2. Set BASE_URL if your backend is not on localhost:8000.
    3. Run:  python seed_listings.py
"""

import json
import requests

# ──────────────────────────────────────────────
#  CONFIG — edit these
# ──────────────────────────────────────────────
ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzcxNDExNDI5LCJpYXQiOjE3NzE0MDc4MjksImp0aSI6IjlhYTNjM2RjNWRjMTRmMDFhOWFkZjlkNjdkNzAyYjcwIiwidXNlcl9pZCI6Ijk2MWRlYmYwLWYzN2QtNDE4NC05ZGUwLTdjOThmM2RmNGM0OSJ9.M-aFIjkognk4_SAHk66WfGrHAp9yHJ0_cu9DTB56-Gg"
BASE_URL = "http://localhost:8000"
# ──────────────────────────────────────────────

ENDPOINT = f"{BASE_URL}/api/v1/listings/"

HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json",
}

LISTINGS = [
    {
        "title": "Serene Mountain Cabin",
        "description": "Escape to the mountains in this cozy log cabin surrounded by pine forests. Features a stone fireplace, wrap-around deck with stunning valley views, and a private hot tub under the stars. Perfect for couples or small families looking for a peaceful retreat.",
        "location": "Asheville, North Carolina",
        "category": "cabins",
        "price_per_night": "185.00",
        "bedrooms": 2,
        "bathrooms": 1.5,
        "max_guests": 4,
        "amenities": ["WiFi", "Fireplace", "Hot Tub", "Kitchen", "Free Parking", "Mountain View", "Hiking Trails"],
        "images": [
            "https://images.unsplash.com/photo-1449158743715-0a90ebb6d2d8?w=800",
            "https://images.unsplash.com/photo-1510798831971-661eb04b3739?w=800",
            "https://images.unsplash.com/photo-1587061949409-02df41d5e562?w=800",
        ],
        "latitude": "35.595100",
        "longitude": "-82.551500",
    },
    {
        "title": "Oceanfront Beach House",
        "description": "Wake up to the sound of waves in this stunning beachfront property. Floor-to-ceiling windows showcase panoramic ocean views. Open-plan living with a chef's kitchen, direct beach access, and a rooftop terrace for unforgettable sunsets.",
        "location": "Malibu, California",
        "category": "beach_houses",
        "price_per_night": "450.00",
        "bedrooms": 4,
        "bathrooms": 3.0,
        "max_guests": 8,
        "amenities": ["WiFi", "Pool", "Kitchen", "Beach Access", "Air Conditioning", "Washer/Dryer", "BBQ Grill", "Surfboard Storage"],
        "images": [
            "https://images.unsplash.com/photo-1499793983690-e29da59ef1c2?w=800",
            "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?w=800",
            "https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=800",
        ],
        "latitude": "34.025900",
        "longitude": "-118.779700",
    },
    {
        "title": "Luxury Hillside Villa",
        "description": "An architectural masterpiece perched above the city. This ultra-modern villa features an infinity pool, home theater, wine cellar, and a private gym. Expansive terraces offer breathtaking skyline views day and night.",
        "location": "Santorini, Greece",
        "category": "luxury_villas",
        "price_per_night": "720.00",
        "bedrooms": 5,
        "bathrooms": 4.5,
        "max_guests": 10,
        "amenities": ["WiFi", "Infinity Pool", "Home Theater", "Wine Cellar", "Gym", "Kitchen", "Air Conditioning", "Concierge Service", "Sea View"],
        "images": [
            "https://images.unsplash.com/photo-1613490493576-7fde63acd811?w=800",
            "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800",
            "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=800",
        ],
        "latitude": "36.393200",
        "longitude": "25.461500",
    },
    {
        "title": "Enchanted Treehouse Retreat",
        "description": "Live among the canopy in this magical treehouse nestled in ancient oaks. Handcrafted with reclaimed wood, it features a glass floor section, rope bridge entrance, and a stargazing loft. A truly one-of-a-kind experience.",
        "location": "Portland, Oregon",
        "category": "treehouses",
        "price_per_night": "210.00",
        "bedrooms": 1,
        "bathrooms": 1.0,
        "max_guests": 2,
        "amenities": ["WiFi", "Heating", "Skylight", "Nature Trails", "Bird Watching", "Breakfast Included"],
        "images": [
            "https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=800",
            "https://images.unsplash.com/photo-1488462237308-ecaa28b729d7?w=800",
            "https://images.unsplash.com/photo-1444080748397-f442aa95c3e5?w=800",
        ],
        "latitude": "45.523100",
        "longitude": "-122.676500",
    },
    {
        "title": "Sustainable Eco Lodge",
        "description": "Immerse yourself in nature at this off-grid eco lodge powered entirely by solar energy. Bamboo construction, organic garden, outdoor rain shower, and guided nature walks included. Disconnect and recharge in paradise.",
        "location": "Tulum, Mexico",
        "category": "eco_lodges",
        "price_per_night": "165.00",
        "bedrooms": 2,
        "bathrooms": 1.0,
        "max_guests": 4,
        "amenities": ["Solar Power", "Organic Garden", "Outdoor Shower", "Yoga Deck", "Bicycle Rental", "Composting", "Beach Access"],
        "images": [
            "https://images.unsplash.com/photo-1596394516093-501ba68a0ba6?w=800",
            "https://images.unsplash.com/photo-1571003123894-1f0594d2b5d9?w=800",
            "https://images.unsplash.com/photo-1540541338287-41700207dee6?w=800",
        ],
        "latitude": "20.214700",
        "longitude": "-87.429200",
    },
    {
        "title": "Alpine Summit Retreat",
        "description": "Perched at 8,000 feet, this luxury mountain retreat offers ski-in/ski-out access, a private sauna, and floor-to-ceiling windows framing snow-capped peaks. After a day on the slopes, unwind by the double-sided fireplace.",
        "location": "Zermatt, Switzerland",
        "category": "mountain_retreats",
        "price_per_night": "550.00",
        "bedrooms": 3,
        "bathrooms": 2.5,
        "max_guests": 6,
        "amenities": ["WiFi", "Sauna", "Fireplace", "Ski Storage", "Kitchen", "Mountain View", "Heated Floors", "Boot Dryer"],
        "images": [
            "https://images.unsplash.com/photo-1502784444783-3a535504c990?w=800",
            "https://images.unsplash.com/photo-1520984032042-162d526883e0?w=800",
            "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=800",
        ],
        "latitude": "46.020700",
        "longitude": "7.749100",
    },
    {
        "title": "Heritage Farmhouse Estate",
        "description": "A beautifully restored 19th-century farmhouse on 50 acres of rolling countryside. Features original stone walls, a country kitchen with an Aga stove, and farm animals the kids will love. Fresh eggs every morning from the henhouse.",
        "location": "Tuscany, Italy",
        "category": "farms",
        "price_per_night": "290.00",
        "bedrooms": 4,
        "bathrooms": 2.0,
        "max_guests": 8,
        "amenities": ["WiFi", "Kitchen", "Farm Animals", "Olive Grove", "Wine Tasting", "Free Parking", "Garden", "Fireplace"],
        "images": [
            "https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=800",
            "https://images.unsplash.com/photo-1416331108676-a22ccb276e35?w=800",
            "https://images.unsplash.com/photo-1464226184884-fa280b87c399?w=800",
        ],
        "latitude": "43.769600",
        "longitude": "11.255800",
    },
    {
        "title": "Industrial Chic Urban Loft",
        "description": "A converted warehouse loft in the arts district featuring 20-foot ceilings, exposed brick, polished concrete floors, and a wall of original factory windows. Walking distance to galleries, restaurants, and nightlife.",
        "location": "Brooklyn, New York",
        "category": "urban_lofts",
        "price_per_night": "320.00",
        "bedrooms": 2,
        "bathrooms": 2.0,
        "max_guests": 4,
        "amenities": ["WiFi", "Air Conditioning", "Kitchen", "Washer/Dryer", "Workspace", "Smart TV", "Elevator", "Rooftop Access"],
        "images": [
            "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800",
            "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800",
            "https://images.unsplash.com/photo-1536376072261-38c75010e6c9?w=800",
        ],
        "latitude": "40.678200",
        "longitude": "-73.944200",
    },
    {
        "title": "Tropical Beach Bungalow",
        "description": "A thatched-roof bungalow steps from crystal-clear turquoise waters. Private deck with hammock, outdoor shower surrounded by tropical plants, and complimentary snorkeling gear. Paradise found.",
        "location": "Bali, Indonesia",
        "category": "beach_houses",
        "price_per_night": "130.00",
        "bedrooms": 1,
        "bathrooms": 1.0,
        "max_guests": 2,
        "amenities": ["WiFi", "Beach Access", "Hammock", "Snorkeling Gear", "Outdoor Shower", "Fan", "Breakfast Included", "Airport Transfer"],
        "images": [
            "https://images.unsplash.com/photo-1439066615861-d1af74d74000?w=800",
            "https://images.unsplash.com/photo-1506929562872-bb421503ef21?w=800",
            "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800",
        ],
        "latitude": "-8.409500",
        "longitude": "115.188900",
    },
    {
        "title": "Rustic Lakeside Cabin",
        "description": "A charming hand-built cabin on the shore of a pristine mountain lake. Comes with a private dock, canoe, and fishing gear. Fall asleep to loons calling and wake up to mist rising off the water. Pure tranquility.",
        "location": "Lake Tahoe, California",
        "category": "cabins",
        "price_per_night": "225.00",
        "bedrooms": 3,
        "bathrooms": 2.0,
        "max_guests": 6,
        "amenities": ["WiFi", "Fireplace", "Kitchen", "Private Dock", "Canoe", "Fishing Gear", "BBQ Grill", "Lake View"],
        "images": [
            "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=800",
            "https://images.unsplash.com/photo-1510798831971-661eb04b3739?w=800",
            "https://images.unsplash.com/photo-1495837174058-628aafc7d610?w=800",
        ],
        "latitude": "39.096800",
        "longitude": "-120.032300",
    },
    {
        "title": "Modern Minimalist Villa",
        "description": "Clean lines and open spaces define this stunning modern villa. Floor-to-ceiling glass walls blur the line between indoors and out. Heated infinity pool, zen garden, and a fully equipped outdoor kitchen for alfresco dining.",
        "location": "Ibiza, Spain",
        "category": "luxury_villas",
        "price_per_night": "680.00",
        "bedrooms": 4,
        "bathrooms": 3.5,
        "max_guests": 8,
        "amenities": ["WiFi", "Infinity Pool", "Kitchen", "Air Conditioning", "Zen Garden", "Outdoor Kitchen", "Smart Home", "Sea View", "DJ Equipment"],
        "images": [
            "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800",
            "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=800",
            "https://images.unsplash.com/photo-1613490493576-7fde63acd811?w=800",
        ],
        "latitude": "38.906700",
        "longitude": "1.420800",
    },
    {
        "title": "Countryside Lavender Farm",
        "description": "Stay amid endless rows of fragrant lavender on this working Provençal farm. The converted barn features rustic beams, a farmhouse kitchen, and a terrace overlooking purple fields stretching to the horizon. Lavender products included.",
        "location": "Provence, France",
        "category": "farms",
        "price_per_night": "195.00",
        "bedrooms": 2,
        "bathrooms": 1.5,
        "max_guests": 4,
        "amenities": ["WiFi", "Kitchen", "Garden", "Farm Tour", "Lavender Products", "Free Parking", "Bicycle Rental", "Patio"],
        "images": [
            "https://images.unsplash.com/photo-1499002238440-d264edd596ec?w=800",
            "https://images.unsplash.com/photo-1416331108676-a22ccb276e35?w=800",
            "https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=800",
        ],
        "latitude": "43.949300",
        "longitude": "5.451200",
    },
    {
        "title": "Skyline Penthouse Loft",
        "description": "A sleek penthouse loft on the 40th floor with 360-degree city views. Open-concept design with designer furniture, a gourmet kitchen island, and floor-to-ceiling windows in every room. Rooftop pool access included.",
        "location": "Dubai, UAE",
        "category": "urban_lofts",
        "price_per_night": "890.00",
        "bedrooms": 3,
        "bathrooms": 3.0,
        "max_guests": 6,
        "amenities": ["WiFi", "Rooftop Pool", "Gym", "Kitchen", "Air Conditioning", "Smart TV", "Concierge", "City View", "Valet Parking"],
        "images": [
            "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800",
            "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800",
            "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=800",
        ],
        "latitude": "25.197200",
        "longitude": "55.274400",
    },
    {
        "title": "Rainforest Eco Treehouse",
        "description": "Elevated among ancient rainforest canopy, this eco-treehouse combines luxury with sustainability. Solar-powered with a composting toilet, outdoor bathtub, and private suspension bridge. Wake up to toucans and howler monkeys.",
        "location": "Costa Rica",
        "category": "treehouses",
        "price_per_night": "175.00",
        "bedrooms": 1,
        "bathrooms": 1.0,
        "max_guests": 2,
        "amenities": ["Solar Power", "Outdoor Bathtub", "Suspension Bridge", "Nature Guides", "Breakfast Included", "Wildlife Watching", "Mosquito Nets"],
        "images": [
            "https://images.unsplash.com/photo-1488462237308-ecaa28b729d7?w=800",
            "https://images.unsplash.com/photo-1444080748397-f442aa95c3e5?w=800",
            "https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=800",
        ],
        "latitude": "10.463400",
        "longitude": "-84.007200",
    },
    {
        "title": "Cliffside Mountain Lodge",
        "description": "Dramatically cantilevered over a mountain gorge, this architectural marvel features glass floors, a heated outdoor pool suspended over the valley, and panoramic views from every room. Adventure and luxury combined.",
        "location": "Queenstown, New Zealand",
        "category": "mountain_retreats",
        "price_per_night": "480.00",
        "bedrooms": 3,
        "bathrooms": 2.5,
        "max_guests": 6,
        "amenities": ["WiFi", "Heated Pool", "Fireplace", "Kitchen", "Mountain View", "Helicopter Pad", "Wine Cellar", "Sauna"],
        "images": [
            "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=800",
            "https://images.unsplash.com/photo-1502784444783-3a535504c990?w=800",
            "https://images.unsplash.com/photo-1520984032042-162d526883e0?w=800",
        ],
        "latitude": "-45.031200",
        "longitude": "168.662600",
    },
    {
        "title": "Desert Oasis Eco Dome",
        "description": "A geodesic dome in the heart of the desert offering uninterrupted stargazing through transparent panels. Solar-powered climate control, an outdoor fire pit, and guided desert excursions available. Silence has never been so luxurious.",
        "location": "Joshua Tree, California",
        "category": "eco_lodges",
        "price_per_night": "245.00",
        "bedrooms": 1,
        "bathrooms": 1.0,
        "max_guests": 2,
        "amenities": ["Solar Power", "Stargazing", "Fire Pit", "Air Conditioning", "Kitchen", "Outdoor Shower", "Desert Tours", "Telescope"],
        "images": [
            "https://images.unsplash.com/photo-1540541338287-41700207dee6?w=800",
            "https://images.unsplash.com/photo-1596394516093-501ba68a0ba6?w=800",
            "https://images.unsplash.com/photo-1571003123894-1f0594d2b5d9?w=800",
        ],
        "latitude": "34.134700",
        "longitude": "-116.313100",
    },
]


def seed():
    created = 0
    failed = 0

    for i, listing in enumerate(LISTINGS, 1):
        resp = requests.post(ENDPOINT, headers=HEADERS, data=json.dumps(listing))

        if resp.status_code == 201:
            data = resp.json()
            print(f"  [{i}/{len(LISTINGS)}] Created: {data['title']}  (id: {data['id']})")
            created += 1
        else:
            print(f"  [{i}/{len(LISTINGS)}] FAILED: {listing['title']}")
            print(f"           Status {resp.status_code}: {resp.text[:200]}")
            failed += 1

    print(f"\nDone — {created} created, {failed} failed.")


if __name__ == "__main__":
    if ACCESS_TOKEN == "PASTE_YOUR_ACCESS_TOKEN_HERE":
        print("ERROR: Set your ACCESS_TOKEN at the top of this script first.")
        raise SystemExit(1)

    print(f"Seeding {len(LISTINGS)} listings to {ENDPOINT}\n")
    seed()
