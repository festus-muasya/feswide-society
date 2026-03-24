from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

class User(db.Model):
    """End-user authentication with persistent Hex ID"""
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(50), unique=True, nullable=False) 
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(100))
    is_confirmed = db.Column(db.Boolean, default=True) # Set to true for auto-registration
    uploads = db.relationship('UserUpload', backref='author', lazy=True)

class Product(db.Model):
    """Verified Answer Repository"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)

class UserUpload(db.Model):
    """Answer submissions linked to unique User ID"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    platform = db.Column(db.String(50)) # Outlier or Handshake
    project_name = db.Column(db.String(100))
    filename = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class AdminUser(db.Model):
    """Role-based access for Superadmin and Subadmins"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='subadmin') 

class SiteConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True)
    value = db.Column(db.Text)