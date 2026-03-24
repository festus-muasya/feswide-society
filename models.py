from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

# Initialize Database Engine
db = SQLAlchemy()

class User(db.Model):
    """
    Standard User Identity Model
    Supports manual registration, password recovery, and Google SSO.
    """
    id = db.Column(db.Integer, primary_key=True)
    # Unique persistent identity starting with '698b'
    public_id = db.Column(db.String(50), unique=True, nullable=False) 
    # google_id used for 'Continue with Google' auto-registration
    google_id = db.Column(db.String(100), unique=True, nullable=True) 
    email = db.Column(db.String(120), unique=True, nullable=False)
    # Password remains nullable to support Google-exclusive logins
    password = db.Column(db.String(200), nullable=True) 
    full_name = db.Column(db.String(100))
    is_confirmed = db.Column(db.Boolean, default=True)
    
    # Secure Password Recovery Tokens
    reset_token = db.Column(db.String(100), nullable=True)
    token_expiry = db.Column(db.DateTime, nullable=True)
    
    # Relationship to track all AI answer submissions per user
    uploads = db.relationship('UserUpload', backref='owner', lazy=True)

class UserUpload(db.Model):
    """
    AI Trajectory Submission Log
    Links user-provided Handshake or Outlier answers to their unique User ID.
    """
    id = db.Column(db.Integer, primary_key=True)
    # Linked to User.id for monitoring specific contributor activity
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    platform = db.Column(db.String(50)) # 'Handshake AI' or 'Outlier AI'
    project_name = db.Column(db.String(100), nullable=False) 
    filename = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class AdminUser(db.Model):
    """
    Command Center Access Control
    Superadmin: FestusMaster2026!
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='subadmin') # 'superadmin' or 'subadmin'

class Product(db.Model):
    """
    Verified Answer Repository
    Stores trajectories for Aether, Blackbeard, Kobra, etc.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)

class Opportunity(db.Model):
    """
    Marketplace and Hiring Board
    Includes tasks and the redirect logic to multimango.com.
    """
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20)) # 'Hiring' or 'Tasker'
    platform = db.Column(db.String(50))
    rate = db.Column(db.String(100))
    whatsapp = db.Column(db.String(50))
    description = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class SiteConfig(db.Model):
    """
    Global Frontend Settings
    Allows Superadmin to update hero text and broadcast alerts.
    """
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)