from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
bcrypt = Bcrypt()

# Import models so they are registered properly
from models.user import User
from models.parking_space import ParkingSpot

