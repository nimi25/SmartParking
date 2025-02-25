from app import app
from models import db, User, ParkingSpot
from datetime import time

# Push the app context
app.app_context().push()

# Create (or get) the owner with email "smpc2004@gmail.com"
owner_email = "smpc2004@gmail.com"
owner = User.query.filter_by(email=owner_email).first()
if not owner:
    owner = User(username="zidxan", email=owner_email, role="owner")
    owner.set_password("12345")
    db.session.add(owner)
    db.session.commit()
    print("Owner created: zidxan (", owner_email, ")")
else:
    print("Owner already exists:", owner_email)

# Define 20 manually chosen parking spots in Bangalore
parking_spots = [
    # Koramangala
    {"location": "Koramangala 1st Block", "lat": 12.9343, "lng": 77.6185},
    {"location": "Koramangala Sony Signal", "lat": 12.9370, "lng": 77.6220},
    {"location": "Koramangala Forum Mall", "lat": 12.9346, "lng": 77.6101},
    {"location": "Koramangala Wipro Park", "lat": 12.9285, "lng": 77.6271},
    {"location": "Koramangala 80 Feet Road", "lat": 12.9387, "lng": 77.6278},

    # Jayanagar
    {"location": "Jayanagar 4th Block", "lat": 12.9280, "lng": 77.5800},
    {"location": "Jayanagar 9th Block", "lat": 12.9186, "lng": 77.5967},
    {"location": "Jayanagar Central Mall", "lat": 12.9204, "lng": 77.5852},
    {"location": "Jayanagar Raghavendra Swamy Mutt", "lat": 12.9243, "lng": 77.5829},
    {"location": "Jayanagar South End Circle", "lat": 12.9248, "lng": 77.5739},

    # Wilson Garden
    {"location": "Wilson Garden 10th Cross", "lat": 12.9507, "lng": 77.5891},
    {"location": "Wilson Garden BMTC Depot", "lat": 12.9486, "lng": 77.5912},
    {"location": "Wilson Garden Hombegowda Nagar", "lat": 12.9465, "lng": 77.5947},
    {"location": "Wilson Garden Lakshmi Road", "lat": 12.9498, "lng": 77.5961},
    {"location": "Wilson Garden NIMHANS Hospital", "lat": 12.9469, "lng": 77.5932},

    # Shivajinagar
    {"location": "Shivajinagar Bus Stand", "lat": 12.9822, "lng": 77.6044},
    {"location": "Shivajinagar Commercial Street", "lat": 12.9815, "lng": 77.6092},
    {"location": "Shivajinagar Russell Market", "lat": 12.9828, "lng": 77.6018},
    {"location": "Shivajinagar St. Mary's Basilica", "lat": 12.9789, "lng": 77.6046},
    {"location": "Shivajinagar Bowring Hospital", "lat": 12.9810, "lng": 77.6023},
]

# Insert into database
spots = []
for i, spot in enumerate(parking_spots):
    new_spot = ParkingSpot(
        location=spot["location"],
        price=50.0 + i * 10,  # Incremental pricing
        availability=True,
        owner_id=owner.id,
        lat=spot["lat"],
        lng=spot["lng"],
        two_wheeler_spaces=5,
        four_wheeler_spaces=2,
        description=f"Secure and convenient parking at {spot['location']}.",
        available_from=time(6, 0),
        available_to=time(22, 0)
    )
    spots.append(new_spot)

db.session.add_all(spots)
db.session.commit()

print("Database populated with 20 well-distributed parking spots in Bangalore!")
