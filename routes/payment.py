from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, PaymentDetails, Booking, ParkingSpot, ParkingSpace, User
from sqlalchemy.orm import joinedload

payment_bp = Blueprint('payment', __name__)

# -------------------- OWNER PAYMENT SETUP ROUTE --------------------
@payment_bp.route('/process', methods=['GET', 'POST'])
@login_required
def process_payment():
    # Only owners should update payment details in this route.
    if current_user.role != 'owner':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('dashboard.dashboard'))

    if request.method == 'GET':
        payment_info = PaymentDetails.query.filter_by(owner_id=current_user.id).first()
        return render_template('payment.html', payment_info=payment_info)
    else:
        upi_id = request.form.get('upi_id')
        phone_number = request.form.get('phone_number')
        # Optionally, handle QR code file upload if needed.
        if not (upi_id or phone_number):
            flash("Please provide valid payment details.", "danger")
            return redirect(url_for('payment.process_payment'))

        payment_info = PaymentDetails.query.filter_by(owner_id=current_user.id).first()
        if payment_info:
            payment_info.upi_id = upi_id
            payment_info.phone_number = phone_number
        else:
            payment_info = PaymentDetails(owner_id=current_user.id, upi_id=upi_id, phone_number=phone_number)
            db.session.add(payment_info)
        db.session.commit()
        flash("Payment details updated successfully!", "success")
        return redirect(url_for('owner.payment'))

# -------------------- DELETE PAYMENT ROUTE --------------------
@payment_bp.route('/delete_payment', methods=['POST'])
@login_required
def delete_payment():
    if current_user.role != 'owner':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('dashboard.dashboard'))

    payment_info = PaymentDetails.query.filter_by(owner_id=current_user.id).first()
    if not payment_info:
        flash("No payment details found to delete.", "danger")
        return redirect(url_for('payment.process_payment'))

    db.session.delete(payment_info)
    db.session.commit()
    flash("Payment details deleted successfully!", "success")
    return redirect(url_for('payment.process_payment'))

# -------------------- DISPLAY PAYMENT DETAILS (for drivers) --------------------
from sqlalchemy.orm import joinedload


@payment_bp.route('/payment_details/<int:booking_id>')
@login_required
def payment_details(booking_id):
    # Retrieve the booking by its id
    booking = Booking.query.get(booking_id)
    if not booking:
        flash("Booking not found.", "danger")
        return redirect(url_for('dashboard.my_bookings'))

    # Retrieve the owner via the parking_space and parking_spot relationship
    owner = booking.parking_space.parking_spot.owner
    # Access the payment_details relationship and take the first element if it's a list
    payment_info = owner.payment_details
    if isinstance(payment_info, list):
        payment_info = payment_info[0] if payment_info else None

    if not payment_info:
        flash("Owner has not set up payment details.", "warning")
        return redirect(url_for('dashboard.my_bookings'))

    # Debug: print retrieved values (remove after testing)
    print("Payment Details - UPI ID:", payment_info.upi_id, "Phone Number:", payment_info.phone_number, "QR Code:",
          payment_info.qr_code)

    return render_template('payment_details.html', payment=payment_info)

