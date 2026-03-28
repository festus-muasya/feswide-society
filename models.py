from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(50), unique=True, nullable=False) # 698b...
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=True)
    full_name = db.Column(db.String(100))
    uploads = db.relationship('UserUpload', backref='owner', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    price = db.Column(db.Float, default=999.0) # Fixed Price
    filename = db.Column(db.String(255), nullable=False)

class UserUpload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    platform = db.Column(db.String(50))
    project_name = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class AdminUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='subadmin')

class Opportunity(db.Model):
    """Hiring and Tasking Marketplace"""
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50)) # 'Hiring' or 'Tasking'
    role = db.Column(db.String(50)) # 'Account Owner', 'Tasker', 'Researcher'
    platform = db.Column(db.String(50)) # 'Handshake', 'Outlier', etc.
    description = db.Column(db.Text)
    contact = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)