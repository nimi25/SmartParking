from flask import Blueprint, render_template, session, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, ParkingSpot, Booking, User

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def dashboard():
    role = session.get('role')

    # --------------- DRIVER DASHBOARD ---------------
    if role == 'driver':
        available_spots = ParkingSpot.query.all()
        booked_spots = Booking.query.filter_by(user_id=current_user.id).all()
        return render_template('driver_dashboard.html', available_spots=available_spots, booked_spots=booked_spots)

    # --------------- OWNER DASHBOARD ---------------
    elif role == 'owner':
        # 1) Get all parking spots for this owner
        spots = ParkingSpot.query.filter_by(owner_id=current_user.id).all()

        # 2) Gather all bookings referencing these spots, along with the driver (User) info
        joined_data = (
            db.session.query(Booking, User, ParkingSpot)
            .join(User, Booking.user_id == User.id)
            .join(ParkingSpot, Booking.spot_id == ParkingSpot.id)
            .filter(ParkingSpot.owner_id == current_user.id)
            .all()
        )

        # 3) Build a list of booking dictionaries with detailed info
        all_bookings = []
        for booking_obj, user_obj, spot_obj in joined_data:
            booking_dict = {
                "driver_name": user_obj.username,      # or user_obj.email
                "email": user_obj.email,
                "spot_location": spot_obj.location,
                # Times
                "created_at": booking_obj.created_at,
                "start_time": booking_obj.start_time,
                "end_time": booking_obj.end_time,
                # Booking status / vehicle
                "vehicle_type": booking_obj.booked_vehicle_type or "N/A",
                "active": booking_obj.active
            }
            all_bookings.append(booking_dict)

        # 4) Calculate dashboard metrics
        # Simple approach: each booking of a spot adds that spot's price to total_revenue
        total_bookings = len(all_bookings)
        total_revenue = sum(spot_obj.price for (b_obj, u_obj, spot_obj) in joined_data)
        active_spots = sum(1 for s in spots if s.availability)

        # 5) Render the owner dashboard with these new variables
        return render_template(
            'owner_dashboard.html',
            spots=spots,
            bookings=all_bookings,
            total_bookings=total_bookings,
            total_revenue=total_revenue,
            active_spots=active_spots
        )

    # --------------- FALLBACK ---------------
    flash("User role not recognized. Please log in again.", "warning")
    return redirect(url_for('auth.login'))
