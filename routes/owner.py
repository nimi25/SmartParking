from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, ParkingSpot, Booking, User
from datetime import datetime
import os

owner_bp = Blueprint('owner', __name__)

@owner_bp.route('/', methods=['GET'])
@login_required
def owner_dashboard():
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard.driver_dashboard'))
    # Get all parking spots for this owner
    spots = ParkingSpot.query.filter_by(owner_id=current_user.id).all()

    # Gather bookings for these spots (join Booking and User)
    joined_data = (
        db.session.query(Booking, User, ParkingSpot)
        .join(User, Booking.user_id == User.id)
        .join(ParkingSpot, Booking.spot_id == ParkingSpot.id)
        .filter(ParkingSpot.owner_id == current_user.id)
        .all()
    )
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
            "active": booking_obj.active
        }
        all_bookings.append(booking_dict)
    total_bookings = len(all_bookings)
    total_revenue = sum(spot_obj.price for (_, _, spot_obj) in joined_data)
    active_spots = sum(1 for s in spots if s.availability)
    return render_template('owner_dashboard.html',
                           spots=spots,
                           bookings=all_bookings,
                           total_bookings=total_bookings,
                           total_revenue=total_revenue,
                           active_spots=active_spots)

@owner_bp.route('/bookings', methods=['GET'])
@login_required
def bookings():
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard.driver_dashboard'))
    joined_data = (
        db.session.query(Booking, User, ParkingSpot)
        .join(User, Booking.user_id == User.id)
        .join(ParkingSpot, Booking.spot_id == ParkingSpot.id)
        .filter(ParkingSpot.owner_id == current_user.id)
        .all()
    )
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
            "active": booking_obj.active
        }
        all_bookings.append(booking_dict)
    return render_template('bookings.html', bookings=all_bookings)

@owner_bp.route('/parkingspace', methods=['GET'])
@login_required
def parkingspace():
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard.driver_dashboard'))
    spots = ParkingSpot.query.filter_by(owner_id=current_user.id).all()
    return render_template('parkingspace.html', spots=spots)

@owner_bp.route('/payment', methods=['GET', 'POST'])
@login_required
def payment():
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard.driver_dashboard'))
    if request.method == 'POST':
        upi_id = request.form.get('upi_id')
        phone_number = request.form.get('phone_number')
        # Update current_user with new payment info (adjust as needed)
        current_user.upi_id = upi_id
        current_user.phone_number = phone_number
        # If a QR code file is uploaded, save it
        qr_code = request.files.get('qr_code')
        if qr_code:
            filename = qr_code.filename
            qr_code.save(os.path.join('static/uploads', filename))
            current_user.qr_code = filename
        db.session.commit()
        flash("Payment info updated successfully!", "success")
        return redirect(url_for('owner.payment'))
    # For GET, render payment page with existing info and dummy overview data
    payment_info = {
        "upi_id": getattr(current_user, "upi_id", ""),
        "phone_number": getattr(current_user, "phone_number", "")
    }
    # Dummy data; in production, calculate these
    last_payment = 500
    last_payment_date = "2025-03-04"
    total_paid = 2500
    pending_invoices = 1
    pending_amount = 300
    refunds = 0
    return render_template('payment.html',
                           payment_info=payment_info,
                           last_payment=last_payment,
                           last_payment_date=last_payment_date,
                           total_paid=total_paid,
                           pending_invoices=pending_invoices,
                           pending_amount=pending_amount,
                           refunds=refunds)

@owner_bp.route('/metrics', methods=['GET'])
@login_required
def metrics():
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard.driver_dashboard'))
    spots = ParkingSpot.query.filter_by(owner_id=current_user.id).all()
    joined_data = (
        db.session.query(Booking, ParkingSpot)
        .join(ParkingSpot, Booking.spot_id == ParkingSpot.id)
        .filter(ParkingSpot.owner_id == current_user.id)
        .all()
    )
    total_bookings = len(joined_data)
    total_revenue = sum(spot_obj.price for (_, spot_obj) in joined_data)
    active_spots = sum(1 for s in spots if s.availability)
    avg_daily_bookings = 0      # Replace with your calculation
    peak_usage_time = "N/A"       # Replace with your calculation
    monthly_growth = 0            # Replace with your calculation
    return render_template('metrics.html',
                           total_bookings=total_bookings,
                           total_revenue=total_revenue,
                           active_spots=active_spots,
                           avg_daily_bookings=avg_daily_bookings,
                           peak_usage_time=peak_usage_time,
                           monthly_growth=monthly_growth)

@owner_bp.route('/history', methods=['GET'])
@login_required
def history():
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard.driver_dashboard'))
    joined_data = (
        db.session.query(Booking, ParkingSpot)
        .join(ParkingSpot, Booking.spot_id == ParkingSpot.id)
        .filter(ParkingSpot.owner_id == current_user.id)
        .all()
    )
    booking_history = [booking_obj for booking_obj, _ in joined_data]
    payment_history = []  # If you have a Payment model, query and pass it here.
    return render_template('history_owner.html',
                           booking_history=booking_history,
                           payment_history=payment_history)

@owner_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def owner_profile():
    if session.get('role') != 'owner':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('dashboard.driver_dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        profile_pic = request.files.get('profile_pic')
        current_user.username = username
        current_user.email = email
        if password:
            from models import bcrypt
            current_user.password = bcrypt.generate_password_hash(password).decode('utf-8')
        if profile_pic:
            filename = profile_pic.filename
            profile_pic.save(os.path.join('static/uploads', filename))
            current_user.profile_pic = filename
        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for('owner.owner_profile'))
    return render_template('profile_owner.html')

# Optionally, add more owner-specific endpoints if needed.
