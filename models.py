from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    role = db.Column(db.String(20), default='user') # superadmin, subadmin, user
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    price = db.Column(db.Float, default=999.0)
    filename = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

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