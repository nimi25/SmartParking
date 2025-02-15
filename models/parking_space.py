from models import db


class ParkingSpot(db.Model):
    __tablename__ = 'parking_spots'

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    availability = db.Column(db.Boolean, default=True)
    google_maps_link = db.Column(db.Text, nullable=True)  # No character limit
    two_wheeler_spaces = db.Column(db.Integer, nullable=True)
    four_wheeler_spaces = db.Column(db.Integer, nullable=True)
    description = db.Column(db.Text, nullable=True)
    available_from = db.Column(db.Time, nullable=True)
    available_to = db.Column(db.Time, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, server_default=db.func.current_timestamp(),
                           onupdate=db.func.current_timestamp())

    # Relationship with the User model
    owner = db.relationship('User', backref=db.backref('parking_spots_owner', lazy=True))

    def __init__(self, location, price, availability, owner_id, google_maps_link=None,
                 two_wheeler_spaces=None, four_wheeler_spaces=None, description=None,
                 available_from=None, available_to=None):
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

