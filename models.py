from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

# Initialize Database Engine
db = SQLAlchemy()

class User(db.Model):
    """
    Core User Identity Model
    Supports standard registration and 'Continue with Google' auto-registration.
    """
    id = db.Column(db.Integer, primary_key=True)
    # Persistent hex ID starting with 698b
    public_id = db.Column(db.String(50), unique=True, nullable=False) 
    # google_id stores the unique identifier from Google SSO
    google_id = db.Column(db.String(100), unique=True, nullable=True) 
    email = db.Column(db.String(120), unique=True, nullable=False)
    # Password is nullable to support Google-only users
    password = db.Column(db.String(200), nullable=True) 
    full_name = db.Column(db.String(100))
    is_confirmed = db.Column(db.Boolean, default=False)
    
    # Relationship to track all AI answer submissions
    uploads = db.relationship('UserUpload', backref='author', lazy=True)

class Product(db.Model):
    """
    Verified Answer Repository
    Stores the free-access trajectories for Aether, Blackbeard, Kobra, etc.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False) # e.g., 'AETHER QUALITY CHECK'
    filename = db.Column(db.String(255), nullable=False) # e.g., 'aether_qc.pdf'
    description = db.Column(db.Text, nullable=True)

class UserUpload(db.Model):
    """
    AI Trajectory Submission Log
    Links user-provided Handshake AI and Outlier AI answers to their User ID.
    """
    id = db.Column(db.Integer, primary_key=True)
    # Linked to User.id to monitor specific contributor activity
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    platform = db.Column(db.String(50)) # 'Handshake AI' or 'Outlier AI'
    project_name = db.Column(db.String(100)) # Exact project name for admin review
    filename = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class AdminUser(db.Model):
    """
    Administrative Access Controls
    Superadmin: full control. Subadmin: monitoring and upload management.
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False) # superadmin: FestusMaster2026!
    role = db.Column(db.String(20), default='subadmin')

class Opportunity(db.Model):
    """
    Marketplace Postings
    Used for the hiring board and redirect logic to multimango.com.
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
    Frontend Configuration
    Used by the Superadmin to update the Milky White hero text.
    """
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)