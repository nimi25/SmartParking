from flask import Blueprint, jsonify
from models import db, ParkingSpot

parking_bp = Blueprint("parking", __name__)

@parking_bp.route('/parking_spots', methods=['GET'])
def get_parking_spots():
    try:
        spots = ParkingSpot.query.all()  # Fetch all parking spots
        result = [
            {
                "id": spot.id,
                "location": spot.location,
                "price": spot.price,
                "availability": spot.availability,
            }
            for spot in spots
        ]
        return jsonify(result), 200  # Return with HTTP 200 (OK)
    except Exception as e:
        return jsonify({"error": str(e)}), 500  # Return error message
