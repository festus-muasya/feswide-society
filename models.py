from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(15), unique=True, nullable=False)
    role = db.Column(db.String(20), default='user') # 'user', 'subadmin', 'superadmin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    price = db.Column(db.Float, nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    checkout_request_id = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    document_name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='Pending')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class UserUpload(db.Model):
    __tablename__ = 'user_uploads'
    id = db.Column(db.Integer, primary_key=True)
    uploader_phone = db.Column(db.String(15), nullable=False)
    platform = db.Column(db.String(50), nullable=False) # Handshake AI or Outlier AI
    project_name = db.Column(db.String(150), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default='Reviewing') 
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

class SearchQuery(db.Model):
    __tablename__ = 'search_queries'
    id = db.Column(db.Integer, primary_key=True)
    query = db.Column(db.String(150), unique=True, nullable=False)
    search_count = db.Column(db.Integer, default=1)