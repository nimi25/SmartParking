from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
bcrypt = Bcrypt()

# Import all models from models.py
from .models import User, ParkingSpot, ParkingSpace, Booking, PaymentDetails

__all__ = [
    "db",
    "bcrypt",
    "User",
    "ParkingSpot",
    "ParkingSpace",
    "Booking",
    "PaymentDetails"
]
