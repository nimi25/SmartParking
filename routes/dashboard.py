from flask import Blueprint, render_template, session, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, ParkingSpot, Booking, User
from sqlalchemy import func

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

        # 2) Gather all bookings for these spots with driver (User) info
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
                "driver_name": user_obj.username,
                "email": user_obj.email,
                "spot_location": spot_obj.location,
                "created_at": booking_obj.created_at,
                "start_time": booking_obj.start_time,
                "end_time": booking_obj.end_time,
                "vehicle_type": booking_obj.booked_vehicle_type or "N/A",
                "active": booking_obj.active,
                "vehicle_number": booking_obj.vehicle_number,  # New field
                "booking_id": booking_obj.booking_id           # New field
            }
            all_bookings.append(booking_dict)

        # 4) Calculate dashboard metrics
        total_bookings = len(all_bookings)
        total_revenue = sum(spot_obj.price for (b_obj, u_obj, spot_obj) in joined_data)
        active_spots = sum(1 for s in spots if s.availability)

        # 5) Render the owner dashboard with these variables
        return render_template(
            'owner_dashboard.html',
            spots=spots,
            bookings=all_bookings,
            total_bookings=total_bookings,
            total_revenue=total_revenue,
            active_spots=active_spots
        )

    # --------------- ADMIN DASHBOARD ---------------
    elif role == 'admin':
        users = User.query.all()
        total_users = User.query.count()
        total_spots = ParkingSpot.query.count()
        available_spots = ParkingSpot.query.filter_by(availability=True).count()
        booked_spots = ParkingSpot.query.filter_by(availability=False).count()
        total_bookings = Booking.query.count()
        revenue = db.session.query(func.sum(ParkingSpot.price)).filter(ParkingSpot.status == 'booked').scalar() or 0
        spots = ParkingSpot.query.all()

        total_two_wheeler = db.session.query(func.sum(ParkingSpot.two_wheeler_spaces)) \
                                .filter(ParkingSpot.availability == True).scalar() or 0
        total_four_wheeler = db.session.query(func.sum(ParkingSpot.four_wheeler_spaces)) \
                                 .filter(ParkingSpot.availability == True).scalar() or 0

        return render_template(
            'admin_dashboard.html',
            users=users,
            total_users=total_users,
            total_spots=total_spots,
            available_spots=available_spots,
            booked_spots=booked_spots,
            total_bookings=total_bookings,
            revenue=revenue,
            total_two_wheeler=total_two_wheeler,
            total_four_wheeler=total_four_wheeler,
            spots=spots
        )

    # --------------- FALLBACK ---------------
    flash("User role not recognized. Please log in again.", "warning")
    return redirect(url_for('auth.login'))
