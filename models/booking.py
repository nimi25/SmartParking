# models/booking.py

from . import db  # from models/__init__.py
from sqlalchemy import Column, Integer, ForeignKey, Time, DateTime, func
from sqlalchemy.orm import relationship

class Booking(db.Model):
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spot.id'), nullable=False)

    two_wheeler = db.Column(db.Integer, default=0)
    four_wheeler = db.Column(db.Integer, default=0)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    # relationships
    user = relationship("User", backref="bookings")
    spot = relationship("ParkingSpot", backref="bookings")

    def __init__(self, user_id, spot_id, two_wheeler, four_wheeler, start_time, end_time):
        self.user_id = user_id
        self.spot_id = spot_id
        self.two_wheeler = two_wheeler
        self.four_wheeler = four_wheeler
        self.start_time = start_time
        self.end_time = end_time
