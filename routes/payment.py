# payment.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
import razorpay
import os

payment_bp = Blueprint('payment', __name__)

# Configure your Razorpay credentials
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', 'your_test_key')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', 'your_test_secret')
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

@payment_bp.route('/process', methods=['GET', 'POST'])
@login_required
def process_payment():
    """
    1. GET request:
       - Comes from the 'Proceed to Payment' button in driver_dashboard.html
       - Displays payment.html where user selects payment option.

    2. POST request:
       - Submits payment.html form with booking_id, amount, payment_option
       - Creates a Razorpay order and renders the Razorpay checkout page.
    """

    if request.method == 'GET':
        # User just clicked 'Proceed to Payment' (via GET form or link)
        booking_id = request.args.get('booking_id')
        amount_str = request.args.get('amount')

        if not booking_id or not amount_str:
            flash("Invalid booking or amount.", "danger")
            return redirect(url_for('dashboard.dashboard'))

        # Show the payment.html page so user can pick a payment option
        return render_template('payment.html',
                               booking_id=booking_id,
                               amount=amount_str)

    # If method == 'POST', user submitted the payment form
    booking_id = request.form.get('booking_id')
    payment_option = request.form.get('payment_option')  # e.g. UPI, card, netbanking
    amount_str = request.form.get('amount')

    try:
        # Razorpay needs amount in paise (multiply rupees by 100)
        amount = int(float(amount_str) * 100)
    except (ValueError, TypeError):
        flash("Invalid amount provided.", "danger")
        return redirect(url_for('dashboard.dashboard'))

    # Create a Razorpay order
    try:
        razorpay_order = razorpay_client.order.create({
            "amount": amount,
            "currency": "INR",
            "payment_capture": "1"  # auto-capture
        })
    except Exception as e:
        flash("Error creating payment order: " + str(e), "danger")
        return redirect(url_for('dashboard.dashboard'))

    order_id = razorpay_order['id']

    # Render a checkout page that automatically opens Razorpay's modal
    return render_template('razorpay_checkout.html',
                           order_id=order_id,
                           amount=amount,
                           booking_id=booking_id,
                           key_id=RAZORPAY_KEY_ID)

@payment_bp.route('/success')
@login_required
def payment_success():
    """
    Called after successful payment from Razorpay's checkout handler.
    You can verify signature here if needed, and then update your DB.
    """
    payment_id = request.args.get('payment_id')
    order_id = request.args.get('order_id')
    signature = request.args.get('signature')

    # TODO: Verify signature if desired, then mark booking as paid in DB.

    flash("Payment successful!", "success")
    return redirect(url_for('dashboard.dashboard'))
