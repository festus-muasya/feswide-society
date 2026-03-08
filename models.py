from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Initialize the database object
db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(15), unique=True, nullable=False)
    role = db.Column(db.String(20), default='user') # Roles: 'user', 'subadmin', 'superadmin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    checkout_request_id = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    document_name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='Pending') # Statuses: 'Pending', 'Paid', 'Failed'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class UserUpload(db.Model):
    __tablename__ = 'user_uploads'
    id = db.Column(db.Integer, primary_key=True)
    uploader_phone = db.Column(db.String(15), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default='Reviewing') # Statuses: 'Reviewing', 'Approved', 'Rejected'
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)