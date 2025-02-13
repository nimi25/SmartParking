from models import db

class ParkingSpot(db.Model):
    __tablename__ = 'parking_spots'
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    availability = db.Column(db.Boolean, default=True)

    # Relationship with the User model
    owner = db.relationship('User', backref=db.backref('parking_spots_owner', lazy=True))

    def __init__(self, location, price, availability, owner_id):
        self.location = location
        self.price = price
        self.availability = availability
        self.owner_id = owner_id
