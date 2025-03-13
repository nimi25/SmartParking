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

# 2) Ensure we have the 'zidowner' user with email "smpc2004@gmail.com"
owner_email = "smpc2004@gmail.com"
owner = User.query.filter_by(email=owner_email).first()

if not owner:
    owner = User(username="zidowner", email=owner_email, role="owner")
    owner.set_password("1234")
    db.session.add(owner)
    db.session.commit()
    print(f"Created new owner: {owner.username} ({owner.email})")
else:
    print(f"Owner already exists: {owner.username} ({owner.email})")

# 3) Define 20 parking spots in Bangalore focusing on hotspots like Jayanagar, Koramangala, Banashankari, and Indiranagar
bangalore_spots = [
    # Jayanagar spots
    {"location": "Jayanagar Park",         "lat": 12.9250, "lng": 77.5938},
    {"location": "Jayanagar Metro",          "lat": 12.9260, "lng": 77.5940},
    {"location": "Jayanagar Shopping",       "lat": 12.9240, "lng": 77.5920},
    {"location": "Jayanagar Main Road",      "lat": 12.9255, "lng": 77.5950},
    {"location": "Jayanagar Residency",      "lat": 12.9265, "lng": 77.5930},

    # Koramangala spots
    {"location": "Koramangala 1st Block",     "lat": 12.9352, "lng": 77.6245},
    {"location": "Koramangala 2nd Block",     "lat": 12.9360, "lng": 77.6250},
    {"location": "Koramangala 3rd Block",     "lat": 12.9345, "lng": 77.6235},
    {"location": "Koramangala IT Hub",        "lat": 12.9358, "lng": 77.6260},
    {"location": "Koramangala Main Road",     "lat": 12.9350, "lng": 77.6240},

    # Banashankari spots
    {"location": "Banashankari 1st Stage",    "lat": 12.9362, "lng": 77.5510},
    {"location": "Banashankari 2nd Stage",    "lat": 12.9370, "lng": 77.5520},
    {"location": "Banashankari Main Road",    "lat": 12.9355, "lng": 77.5500},
    {"location": "Banashankari Market",       "lat": 12.9365, "lng": 77.5515},
    {"location": "Banashankari Bus Stop",     "lat": 12.9375, "lng": 77.5530},

    # Indiranagar spots
    {"location": "Indiranagar Metro",         "lat": 12.9716, "lng": 77.6412},
    {"location": "Indiranagar 100 Feet Road",   "lat": 12.9720, "lng": 77.6420},
    {"location": "Indiranagar Market",          "lat": 12.9710, "lng": 77.6400},
    {"location": "Indiranagar Restaurant Area", "lat": 12.9725, "lng": 77.6418},
    {"location": "Indiranagar Tech Park",       "lat": 12.9718, "lng": 77.6425},
]

# 4) Insert these 20 spots into the DB
spots_to_add = []
base_price = 50.0

for i, spot in enumerate(bangalore_spots):
    new_spot = ParkingSpot(
        location=spot["location"],
        price=base_price + (i * 10),  # e.g., 50, 60, 70, ...
        availability=True,
        owner_id=owner.id,
        lat=spot["lat"],
        lng=spot["lng"],
        two_wheeler_spaces=5,
        four_wheeler_spaces=2,
        description=f"Secure parking in Bangalore at {spot['location']}.",
        available_from=time(6, 0),
        available_to=time(22, 0)
    )
    spots_to_add.append(new_spot)

db.session.add_all(spots_to_add)
db.session.commit()

print("Populated DB with 20 parking spots in Bangalore focusing on hotspots!")
