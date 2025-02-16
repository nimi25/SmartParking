from models import db, bcrypt
from flask_login import UserMixin
from sqlalchemy import func


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, server_default=func.current_timestamp())
    updated_at = db.Column(db.DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    def __init__(self, username, email, password, role):
        self.username = username
        self.email = email
        self.set_password(password)
        self.role = role

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)
