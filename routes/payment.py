from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, PaymentDetails, Booking

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
@payment_bp.route('/payment_details/<int:booking_id>')
@login_required
def payment_details(booking_id):
    booking = Booking.query.get(booking_id)
    if not booking:
        flash("Booking not found.", "danger")
        return redirect(url_for('dashboard.my_bookings'))
    payment_info = booking.spot.owner.payment_details
    if not payment_info:
        flash("Owner has not set up payment details.", "warning")
        return redirect(url_for('dashboard.my_bookings'))
    return render_template('payment_details.html', payment=payment_info)
