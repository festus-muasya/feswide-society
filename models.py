from flask_sqlalchemy import SQLAlchemy
import uuid
from datetime import datetime

# Initialize Database
db = SQLAlchemy()

class Product(db.Model):
    """
    Verified Module Repository
    Stores documents such as Grand Prix, Blackbeard, Cacatua Chorus, and White Claw.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    price = db.Column(db.Float, nullable=False) # Displayed as Green Pricing
    filename = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)

class UserUpload(db.Model):
    """
    Answer Submissions for KES 500 Reward
    Stores submissions from users looking to earn by providing trajectories.
    """
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50))
    project_name = db.Column(db.String(100))
    payment_id = db.Column(db.String(100)) # M-Pesa Number for payout
    filename = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class AdminUser(db.Model):
    """
    Command Center Access Controls
    The 'superadmin' role enables the Marketplace Moderator to delete user posts.
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='subadmin') 

class ActivityLog(db.Model):
    """Operator Action Tracking to log admin activities"""
    id = db.Column(db.Integer, primary_key=True)
    operator = db.Column(db.String(50), nullable=False)
    action = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Transaction(db.Model):
    """Payment Gateway Logs for M-Pesa STK Push tracking"""
    id = db.Column(db.Integer, primary_key=True)
    checkout_request_id = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(50))
    amount = db.Column(db.Float, nullable=False)
    product_id = db.Column(db.Integer)
    payment_method = db.Column(db.String(20), default='M-Pesa')
    status = db.Column(db.String(50), default='Pending')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class SiteConfig(db.Model):
    """
    Global Broadcast Alert System
    Used for the Milky White theme dashboard alerts (without the SYSTEM STATUS prefix).
    """
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)

class Opportunity(db.Model):
    """
    Hiring & Tasker Marketplace Boards
    Stores user-submitted posts that the superadmin can moderate or delete.
    """
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20)) # 'Hiring' or 'Tasker'
    platform = db.Column(db.String(50)) # Outlier AI or Handshake AI
    rate = db.Column(db.String(100)) # Commission/Salary
    whatsapp = db.Column(db.String(50)) # Public Contact link
    description = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class ChatTicket(db.Model):
    """
    Agent John Error Tickets
    Modern support system requiring a WhatsApp number for error reporting.
    """
    id = db.Column(db.Integer, primary_key=True)
    whatsapp = db.Column(db.String(50), nullable=False)
    error_desc = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)