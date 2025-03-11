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
    role = db.Column(db.Text, nullable=False)

    # Timestamps
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
    __tablename__ = 'parking_spot'  # ✅ Matches your database table name

    id = db.Column(db.Integer, primary_key=True)
    booked_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='available')
    location = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    availability = db.Column(db.Boolean, default=True)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
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

# ------------------- BOOKING MODEL -------------------
class Booking(db.Model):
    __tablename__ = 'booking'  # ✅ Matches your database table name

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spot.id'), nullable=False)
    two_wheeler = db.Column(db.Integer, default=0)
    four_wheeler = db.Column(db.Integer, default=0)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    booked_vehicle_type = db.Column(db.String(50))
    vehicle_number = db.Column(db.String(20))
    status = db.Column(db.String(20), default='Pending')

    # Relationships
    spot = db.relationship('ParkingSpot', backref='booking')
    user = db.relationship('User', backref='booking')

# ------------------- PAYMENT DETAILS MODEL -------------------
class PaymentDetails(db.Model):
    __tablename__ = 'payment_details'

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    upi_id = db.Column(db.String(100), nullable=False, unique=True)
    phone_number = db.Column(db.String(15), nullable=False)
    qr_code = db.Column(db.String(255))

    # Timestamps
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship
    owner = db.relationship('User', backref='payment_details')
