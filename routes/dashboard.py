from flask import Blueprint, render_template, session, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, ParkingSpot, Booking, User, ParkingSpace
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from types import SimpleNamespace
from datetime import datetime

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/', endpoint='driver_dashboard')
@login_required
def dashboard():
    role = session.get('role')
    if role == 'driver':
        available_spots = ParkingSpot.query.all()
        booked_spots = Booking.query.options(
            joinedload(Booking.parking_space).joinedload(ParkingSpace.parking_spot)
        ).filter_by(user_id=current_user.id).all()
        return render_template('driver_dashboard.html',
                               available_spots=available_spots,
                               booked_spots=booked_spots)
    elif role == 'owner':
        spots = ParkingSpot.query.filter_by(owner_id=current_user.id).all()
        joined_data = (
            db.session.query(Booking, User, ParkingSpace, ParkingSpot)
            .join(User, Booking.user_id == User.id)
            .join(ParkingSpace, Booking.parking_space_id == ParkingSpace.id)
            .join(ParkingSpot, ParkingSpace.parking_spot_id == ParkingSpot.id)
            .filter(ParkingSpot.owner_id == current_user.id)
            .all()
        )
        all_bookings = []
        for b, u, ps, s in joined_data:
            booking_dict = {
                "id": b.id,
                "driver_name": u.username,
                "email": u.email,
                "vehicle_number": b.vehicle_number,
                "spot_location": s.location,
                "spot_price": s.price,
                "spot_lat": s.lat,
                "spot_lng": s.lng,
                "created_at": b.created_at,
                "start_time": b.start_time,
                "end_time": b.end_time,
                "vehicle_type": ps.vehicle_type,
                "sub_spot_number": ps.sub_spot_number,
                "active": b.active,
                "status": b.status,
                "session_id": b.session_id if b.session_id is not None else str(b.id),
                "phone_number": b.phone_number
            }
            all_bookings.append(SimpleNamespace(**booking_dict))
        total_bookings = len(all_bookings)
        total_revenue = sum(s.price for (_, _, _, s) in joined_data)
        active_spots = sum(1 for s in spots if s.availability)
        return render_template('owner_dashboard.html',
                               spots=spots,
                               bookings=all_bookings,
                               total_bookings=total_bookings,
                               total_revenue=total_revenue,
                               active_spots=active_spots)
    elif role == 'admin':
        users = User.query.all()
        total_users = User.query.count()
        total_spots = ParkingSpot.query.count()
        available_spots = ParkingSpot.query.filter_by(availability=True).count()
        booked_spots = ParkingSpot.query.filter_by(availability=False).count()
        total_bookings = Booking.query.count()
        revenue = db.session.query(func.sum(ParkingSpot.price))\
                      .filter(ParkingSpot.status == 'booked').scalar() or 0
        spots = ParkingSpot.query.all()
        total_two_wheeler = 0
        total_four_wheeler = 0
        return render_template('admin_dashboard.html',
                               users=users,
                               total_users=total_users,
                               total_spots=total_spots,
                               available_spots=available_spots,
                               booked_spots=booked_spots,
                               total_bookings=total_bookings,
                               revenue=revenue,
                               total_two_wheeler=total_two_wheeler,
                               total_four_wheeler=total_four_wheeler,
                               spots=spots)
    flash("User role not recognized. Please log in again.", "warning")
    return redirect(url_for('auth.login'))

@dashboard_bp.route('/my_bookings')
@login_required
def my_bookings():
    now_dt = datetime.now()
    # Retrieve all bookings for the driver (active flag may still be True even if time has passed)
    bookings = Booking.query.options(
        joinedload(Booking.parking_space).joinedload(ParkingSpace.parking_spot)
    ).filter_by(user_id=current_user.id).all()

    active_bookings = {}
    completed_bookings = {}
    expired_bookings = {}
    for b in bookings:
        session_key = b.session_id if b.session_id is not None else str(b.id)
        # Ensure start_time and end_time are full datetime objects.
        if isinstance(b.start_time, datetime):
            start_dt = b.start_time
        else:
            start_dt = datetime.combine(b.created_at.date(), b.start_time)
        if isinstance(b.end_time, datetime):
            end_dt = b.end_time
        else:
            end_dt = datetime.combine(b.created_at.date(), b.end_time)
        # Build the details dictionary as used in the template.
        details = {
            "id": b.id,
            "vehicle_number": b.vehicle_number,
            "created_at": b.created_at,
            "start_time": b.start_time,  # Original value for formatting in template
            "end_time": b.end_time,      # Original value for formatting in template
            "status": b.status,
            "vehicle_type": b.parking_space.vehicle_type,
            "sub_spot_number": b.parking_space.sub_spot_number,
            "spot_location": b.parking_space.parking_spot.location,
            "spot_price": b.parking_space.parking_spot.price,
            "spot_lat": b.parking_space.parking_spot.lat,
            "spot_lng": b.parking_space.parking_spot.lng,
            "spot_description": b.parking_space.parking_spot.description,
            "booking_id": "BK" + b.created_at.strftime('%d%H%M%S') + (b.vehicle_number[-2:] if b.vehicle_number else str(b.id)),
            "session_id": session_key,
            "phone_number": b.phone_number,
            # Include computed datetimes for internal comparison if needed.
            "start_dt": start_dt,
            "end_dt": end_dt
        }
        # Group the booking based on status.
        if b.status.lower() == "expired":
            expired_bookings.setdefault(session_key, []).append(details)
        elif end_dt > now_dt and b.active:
            active_bookings.setdefault(session_key, []).append(details)
        else:
            completed_bookings.setdefault(session_key, []).append(details)

    current_date = datetime.utcnow().strftime('%Y-%m-%d')
    return render_template("my_bookings.html",
                           active_bookings=active_bookings,
                           completed_bookings=completed_bookings,
                           expired_bookings=expired_bookings,
                           current_date=current_date)

@dashboard_bp.route('/owner/bookings')
@login_required
def owner_bookings():
    if session.get('role') != 'owner':
        flash("Unauthorized", "danger")
        return redirect(url_for('dashboard.dashboard'))
    joined_data = (
        db.session.query(Booking, User, ParkingSpace, ParkingSpot)
        .join(User, Booking.user_id == User.id)
        .join(ParkingSpace, Booking.parking_space_id == ParkingSpace.id)
        .join(ParkingSpot, ParkingSpace.parking_spot_id == ParkingSpot.id)
        .filter(ParkingSpot.owner_id == current_user.id)
        .all()
    )
    all_bookings = []
    for b, u, ps, s in joined_data:
        booking_dict = {
            "id": b.id,
            "driver_name": u.username,
            "email": u.email,
            "vehicle_number": b.vehicle_number,
            "spot_location": s.location,
            "spot_price": s.price,
            "spot_lat": s.lat,
            "spot_lng": s.lng,
            "created_at": b.created_at,
            "start_time": b.start_time,
            "end_time": b.end_time,
            "vehicle_type": ps.vehicle_type,
            "sub_spot_number": ps.sub_spot_number,
            "active": b.active,
            "status": b.status,
            "session_id": b.session_id if b.session_id is not None else str(b.id),
            "phone_number": b.phone_number
        }
        all_bookings.append(SimpleNamespace(**booking_dict))
    grouped_bookings = {}
    for booking in all_bookings:
        grouped_bookings.setdefault(booking.session_id, []).append(booking)
    return render_template("bookings.html", grouped_bookings=grouped_bookings)

@dashboard_bp.route('/history_driver', endpoint='history_driver')
@login_required
def history_driver():
    if session.get('role') != 'driver':
        flash("Unauthorized", "warning")
        return redirect(url_for('dashboard.dashboard'))
    booking_history = Booking.query.filter_by(user_id=current_user.id).all()
    payment_history = []  # Adjust as needed
    return render_template('history_driver.html', booking_history=booking_history, payment_history=payment_history)

dashboard_bp.add_url_rule('/', endpoint='dashboard')
