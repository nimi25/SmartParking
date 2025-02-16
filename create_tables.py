# create_tables.py

from app import app, db
# IMPORTANT: import your models so they're registered in db.metadata
from models import User, ParkingSpot, Booking

def main():
    print("App URI:", app.config["SQLALCHEMY_DATABASE_URI"])
    with app.app_context():
        print("Dropping all tables...")
        db.drop_all()   # CAREFUL: deletes everything
        print("Creating all tables...")
        db.create_all()
        print("Done!")

if __name__ == "__main__":
    main()
