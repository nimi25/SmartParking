# models.py

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from flask_bcrypt import Bcrypt
from sqlalchemy import func
from . import db
bcrypt = Bcrypt()

# ------------------- USER MODEL -------------------
class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'driver' or 'owner'

    # Timestamps using func.now() (DB sets them automatically)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __init__(self, username, email, role):
        self.username = username
        self.email = email
        self.role = role

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)


# ----------------- PARKING SPOT MODEL -----------------
class ParkingSpot(db.Model):
    __tablename__ = 'parking_spot'

    id = db.Column(db.Integer, primary_key=True)
    booked_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # User who booked it
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='available')  # "available" or "booked"
    location = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    availability = db.Column(db.Boolean, default=True)
    google_maps_link = db.Column(db.String(500))
    two_wheeler_spaces = db.Column(db.Integer, default=0)
    four_wheeler_spaces = db.Column(db.Integer, default=0)
    description = db.Column(db.Text)
    available_from = db.Column(db.Time)
    available_to = db.Column(db.Time)

    # Timestamps
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    owner = db.relationship('User', foreign_keys=[owner_id], backref='owned_spots')
    booked_user = db.relationship('User', foreign_keys=[booked_by], backref='booked_spots', lazy=True)

    def __init__(
            self,
            location,
            price,
            availability,
            owner_id,
            google_maps_link=None,
            two_wheeler_spaces=0,
            four_wheeler_spaces=0,
            description=None,
            available_from=None,
            available_to=None
    ):
        self.location = location
        self.price = price
        self.availability = availability
        self.owner_id = owner_id
        self.google_maps_link = google_maps_link
        self.two_wheeler_spaces = two_wheeler_spaces
        self.four_wheeler_spaces = four_wheeler_spaces
        self.description = description
        self.available_from = available_from
        self.available_to = available_to

# ------------------- BOOKING MODEL -------------------
class Booking(db.Model):
    __tablename__ = 'booking'  # or 'bookings', if you prefer plural

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spot.id'), nullable=False)

    two_wheeler = db.Column(db.Integer, default=0)
    four_wheeler = db.Column(db.Integer, default=0)
    start_time = db.Column(db.Time, nullable=False)

    active = db.Column(db.Boolean, default=True)  # Add this field
    end_time = db.Column(db.Time, nullable=False)

    # Timestamp for booking creation
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    # Relationship back to ParkingSpot and User
    spot = db.relationship('ParkingSpot', backref='booking')
    user = db.relationship('User', backref='booking')

    def __init__(self, user_id, spot_id, two_wheeler, four_wheeler, start_time, end_time):
        self.user_id = user_id
        self.spot_id = spot_id
        self.two_wheeler = two_wheeler
        self.four_wheeler = four_wheeler
        self.start_time = start_time
        self.end_time = end_time