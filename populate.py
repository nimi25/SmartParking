from app import app
from models import db, User, ParkingSpot
from datetime import time

# Make sure your Flask config has:
# SQLALCHEMY_DATABASE_URI = "postgresql://postgres:student@localhost:5432/smart_parking_db"

# Push the Flask app context
app.app_context().push()

# 1) Delete ALL existing parking spots
print("Deleting all existing parking spots...")
ParkingSpot.query.delete()
db.session.commit()

# 2) Ensure we have the 'nimi' user with email "nimisha123@gmail.com"
owner_email = "nimisha123@gmail.com"
owner = User.query.filter_by(email=owner_email).first()

if not owner:
    owner = User(username="nimi", email=owner_email, role="owner")
    owner.set_password("nimi")  # or any password you want
    db.session.add(owner)
    db.session.commit()
    print(f"Created new owner: {owner.username} ({owner.email})")
else:
    print(f"Owner already exists: {owner.username} ({owner.email})")

# 3) Define 10 named parking spots in Digboi, Assam
digboi_spots = [
    {"location": "Digboi Oil Refinery",      "lat": 27.382, "lng": 95.619},
    {"location": "Digboi War Cemetery",      "lat": 27.383, "lng": 95.615},
    {"location": "Digboi Market",            "lat": 27.385, "lng": 95.612},
    {"location": "Digboi College",           "lat": 27.388, "lng": 95.610},
    {"location": "Digboi Golf Course",       "lat": 27.390, "lng": 95.614},
    {"location": "Digboi Heritage Park",     "lat": 27.392, "lng": 95.617},
    {"location": "Digboi Centenary Museum",  "lat": 27.384, "lng": 95.613},
    {"location": "Digboi Station Road",      "lat": 27.389, "lng": 95.611},
    {"location": "Digboi Church Road",       "lat": 27.386, "lng": 95.609},
    {"location": "Digboi Lekhapani Road",    "lat": 27.391, "lng": 95.608},
]

# 4) Insert these 10 spots into the DB
spots_to_add = []
base_price = 50.0

for i, spot in enumerate(digboi_spots):
    new_spot = ParkingSpot(
        location=spot["location"],
        price=base_price + (i * 10),  # e.g., 50, 60, 70, ...
        availability=True,
        owner_id=owner.id,
        lat=spot["lat"],
        lng=spot["lng"],
        two_wheeler_spaces=5,
        four_wheeler_spaces=2,
        description=f"Secure parking in Digboi at {spot['location']}.",
        available_from=time(6, 0),
        available_to=time(22, 0)
    )
    spots_to_add.append(new_spot)

db.session.add_all(spots_to_add)
db.session.commit()

print("Populated DB with 10 named parking spots in Digboi, Assam!")
