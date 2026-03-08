import os, requests, base64, hmac, hashlib, time, random, string, json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, abort
from models import db, UserUpload, Product, AdminUser, Transaction, Opportunity, ChatTicket
from werkzeug.utils import secure_filename
from supabase import create_client, Client

app = Flask(__name__)

# --- CONFIG ---
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:////tmp/feswide_v8.db').replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'feswide_enc_2026_prod'
db.init_app(app)

# --- CHATBOT JOHN LOGIC ---
@app.route('/api/john', methods=['POST'])
def john_chat():
    data = request.json
    msg = data.get('message', '').lower()
    
    # Error Handling Flow
    if data.get('is_error'):
        new_ticket = ChatTicket(whatsapp=data.get('whatsapp'), error_desc=msg)
        db.session.add(new_ticket)
        db.session.commit()
        return jsonify({"reply": "I have logged your error to the Admin Dashboard. A specialist will contact you via WhatsApp shortly."})

    if "hello" in msg or "hi" in msg:
        return jsonify({"reply": "Hello! I am John. I can help you with opportunities, pricing, or technical errors. What do you need?"})
    elif "opportunity" in msg or "paid" in msg or "500" in msg:
        return jsonify({"reply": "You can earn KES 500 per verified answer trajectory. Click the orange 'OPPORTUNITIES' button at the top to submit your work."})
    elif "price" in msg or "cost" in msg:
        return jsonify({"reply": "All verified modules are priced at KES 999.0. They are tested and 100% accurate."})
    elif "error" in msg or "problem" in msg or "not working" in msg:
        return jsonify({"ask_error": True, "reply": "I'm sorry to hear that. Please describe the error precisely and provide your WhatsApp number so we can fix it for you."})
    else:
        return jsonify({"reply": "I'm not sure I understand. Type 'error' if you need help, or 'price' for info on our modules."})

# Marketplace Routes
@app.route('/post-opp', methods=['POST'])
def post_opp():
    new_opp = Opportunity(
        type=request.form.get('type'),
        platform=request.form.get('platform'),
        rate=request.form.get('rate'),
        whatsapp=request.form.get('whatsapp'),
        description=request.form.get('desc')
    )
    db.session.add(new_opp)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/')
def index():
    prods = Product.query.all()
    hiring = Opportunity.query.filter_by(type='Hiring').all()
    taskers = Opportunity.query.filter_by(type='Tasker').all()
    return render_template('index.html', products=prods, hiring=hiring, taskers=taskers)

# [Admin and Payment routes remain as per previous secure versions]

if __name__ == '__main__':
    app.run(debug=True)