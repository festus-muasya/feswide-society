from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

class SiteConfig(db.Model):
    __tablename__ = 'site_config'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    price = db.Column(db.Float, default=999.0)
    filename = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    checkout_request_id = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='Pending') 
    download_token = db.Column(db.String(100), unique=True, default=lambda: str(uuid.uuid4()))
    download_count = db.Column(db.Integer, default=0) 
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class UserUpload(db.Model):
    __tablename__ = 'user_uploads'
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50), nullable=False)
    project_name = db.Column(db.String(150), nullable=False)
    mpesa_number = db.Column(db.String(15), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default='Reviewing')
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

class ProjectRequest(db.Model):
    __tablename__ = 'project_requests'
    id = db.Column(db.Integer, primary_key=True)
    project_name = db.Column(db.String(150), nullable=False)
    platform = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AdminUser(db.Model):
    __tablename__ = 'admin_users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default='subadmin')
    is_active = db.Column(db.Boolean, default=True)

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    id = db.Column(db.Integer, primary_key=True)
    operator = db.Column(db.String(50), nullable=False)
    action = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)