from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user
from models import db, User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form.get("password")
        role = request.form['role']  # 'driver' or 'owner'

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered. Please log in.", "danger")
            return redirect(url_for('auth.login'))

        # Ensure password hashing before storing
        new_user = User(username=username, email=email, role=role)
        new_user.set_password(password)  # Ensure this method exists in User model

        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for('auth.login'))

    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):  # Ensure User model has check_password()
            login_user(user)
            session['role'] = user.role
            return redirect(url_for('dashboard.dashboard'))  # Ensure dashboard exists
        else:
            flash("Invalid email or password. Please try again.", "danger")

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    logout_user()
    return redirect(url_for('auth.login'))
