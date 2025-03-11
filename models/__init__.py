from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
bcrypt = Bcrypt()

# Import everything from models.py
from .models import User, ParkingSpot, Booking, PaymentDetails

__all__ = [
    "db",
    "bcrypt",
    "User",
    "ParkingSpot",
    "Booking",
    "PaymentDetails"
]
