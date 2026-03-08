from flask_sqlalchemy import SQLAlchemy
import uuid
from datetime import datetime

db = SQLAlchemy()

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    price = db.Column(db.Float, nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)

class UserUpload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50))
    project_name = db.Column(db.String(100))
    mpesa_number = db.Column(db.String(100))
    filename = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class AdminUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='subadmin')
    is_active = db.Column(db.Boolean, default=True)

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    operator = db.Column(db.String(50), nullable=False)
    action = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    checkout_request_id = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(50), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    payment_method = db.Column(db.String(20), default='M-Pesa')
    status = db.Column(db.String(50), default='Pending')
    download_token = db.Column(db.String(100), default=lambda: str(uuid.uuid4()), unique=True)
    ip_address = db.Column(db.String(50), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class SiteConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)

class Opportunity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20)) # Hiring / Tasker
    platform = db.Column(db.String(50)) # Outlier / Handshake
    rate = db.Column(db.String(50))
    whatsapp = db.Column(db.String(50))
    status = db.Column(db.String(20), default='Active')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)