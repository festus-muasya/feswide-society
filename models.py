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
    payment_id = db.Column(db.String(100)) # M-Pesa or Binance UID
    filename = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Opportunity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20)) # 'Hiring' or 'Tasker'
    platform = db.Column(db.String(50)) # 'Outlier' or 'Handshake'
    rate = db.Column(db.String(100))
    whatsapp = db.Column(db.String(50))
    description = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class ChatTicket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    whatsapp = db.Column(db.String(50))
    error_desc = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class AdminUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(255))
    role = db.Column(db.String(20))

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    checkout_request_id = db.Column(db.String(100), unique=True)
    amount = db.Column(db.Float)
    payment_method = db.Column(db.String(20))
    status = db.Column(db.String(50), default='Pending')
    download_token = db.Column(db.String(100), default=lambda: str(uuid.uuid4()))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)