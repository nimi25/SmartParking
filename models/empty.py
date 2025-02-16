@app.route('/book/<int:spot_id>', methods=['POST'])
@login_required
def book_spot(spot_id):
    # Only drivers can book
    if session.get('role') != 'driver':
        flash("Only drivers can book spots.", "danger")
        return redirect(url_for('dashboard'))

    spot = ParkingSpot.query.get_or_404(spot_id)

    try:
        two_wheeler = int(request.form.get('two_wheeler', 0))
        four_wheeler = int(request.form.get('four_wheeler', 0))
    except ValueError:
        flash("Please enter valid numbers for spot counts.", "danger")
        return redirect(url_for('dashboard'))

    booking_start = request.form.get('booking_start')
    booking_end = request.form.get('booking_end')
    try:
        booking_start_time = datetime.strptime(booking_start, "%H:%M").time()
        booking_end_time = datetime.strptime(booking_end, "%H:%M").time()
    except ValueError:
        flash("Invalid time format. Please use HH:MM.", "danger")
        return redirect(url_for('dashboard'))

    if spot.available_from and spot.available_to:
        if booking_start_time < spot.available_from or booking_end_time > spot.available_to:
            flash("Booking time must be within the available hours.", "danger")
            return redirect(url_for('dashboard'))

    # Create a booking record (optional)
    new_booking = Booking(
        user_id=current_user.id,
        spot_id=spot.id,
        two_wheeler=two_wheeler,
        four_wheeler=four_wheeler,
        start_time=booking_start_time,
        end_time=booking_end_time
    )
    db.session.add(new_booking)

    # Mark the spot as fully booked immediately
    spot.availability = False
    db.session.commit()

    flash("Booking successful!", "success")
    return redirect(url_for('dashboard'))


@app.route('/cancel_booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get(booking_id)

    if not booking:
        flash("Booking not found!", "danger")
        return redirect(url_for('dashboard'))

    # Ensure the user owns the booking (if driver) or is the owner of the spot
    if current_user.role == 'driver' and booking.user_id != current_user.id:
        flash("You can only cancel your own bookings!", "danger")
        return redirect(url_for('dashboard'))

    if current_user.role == 'owner':
        spot = ParkingSpot.query.get(booking.spot_id)
        if not spot or spot.owner_id != current_user.id:
            flash("You can only cancel bookings for your own spots!", "danger")
            return redirect(url_for('dashboard'))

            # Update the status of the parking spot to 'available'
        spot = ParkingSpot.query.get(booking.spot_id)
        if spot:
            spot.status = 'available'

    # Delete the booking to make the spot available again
    db.session.delete(booking)
    db.session.commit()

    flash("Booking canceled successfully! The spot is now available again.", "success")
    return redirect(url_for('dashboard'))

