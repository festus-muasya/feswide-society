import os, requests, base64, hmac, hashlib, time, random, string, json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, abort
from models import db, UserUpload, Product, AdminUser, ActivityLog, Transaction, SiteConfig, Opportunity, ChatTicket
from werkzeug.utils import secure_filename
from supabase import create_client, Client

app = Flask(__name__)

# --- CONFIG ---
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:////tmp/feswide_final.db').replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'feswide_enc_2026_prod'
db.init_app(app)

# --- BOOTSTRAP ---
with app.app_context():
    try:
        db.create_all()
        if not AdminUser.query.filter_by(username='superadmin').first():
            db.session.add(AdminUser(username='superadmin', password='FeswideMaster2026!', role='superadmin'))
        if not SiteConfig.query.filter_by(key='hero_text').first():
            db.session.add(SiteConfig(key='hero_text', value="Feswide Society Index. Secure OPSEC Modules."))
        
        # Restore Official Inventory
        if not Product.query.first():
            db.session.add_all([
                Product(name="AETHER MULTILINGUAL QUALITY CHECK", price=999.0, filename="aether.pdf", description="Tested and they are 100% accurate"),
                Product(name="AETHER CODER SCREENING", price=999.0, filename="coder.pdf", description="Tested and they are 100% accurate"),
                Product(name="KOBRA CLIPS", price=999.0, filename="kobra.pdf", description="Tested and they are 100% accurate"),
                Product(name="GRAND PRIX", price=999.0, filename="gp.pdf", description="Tested and they are 100% accurate")
            ])
        db.session.commit()
    except: pass

# --- CHATBOT JOHN ---
@app.route('/api/john', methods=['POST'])
def john_chat():
    data = request.json
    msg = data.get('message', '').lower()
    
    if data.get('is_error'):
        db.session.add(ChatTicket(whatsapp=data.get('whatsapp'), error_desc=msg))
        db.session.commit()
        return jsonify({"reply": "Error logged. Admin will contact you on WhatsApp."})

    if "hello" in msg: return jsonify({"reply": "I am John. Need help with opportunities, pricing, or errors?"})
    if "price" in msg: return jsonify({"reply": "All modules are KES 999.0 and 100% accurate."})
    if "error" in msg: return jsonify({"ask_error": True, "reply": "Please describe the error and provide your WhatsApp number."})
    return jsonify({"reply": "I can assist with modules or opportunities. Type 'error' if you need technical support."})

# --- ROUTES ---
@app.route('/')
def index():
    conf = SiteConfig.query.filter_by(key='hero_text').first()
    return render_template('index.html', 
                           products=Product.query.all(), 
                           hiring=Opportunity.query.filter_by(type='Hiring').all(),
                           taskers=Opportunity.query.filter_by(type='Tasker').all(),
                           config_text=conf.value if conf else "")

@app.route('/admin')
def admin():
    if 'role' not in session: return redirect(url_for('login'))
    return render_template('admin.html', 
                           txns=Transaction.query.order_by(Transaction.id.desc()).all(),
                           products=Product.query.all(),
                           tickets=ChatTicket.query.order_by(ChatTicket.id.desc()).all(),
                           role=session['role'], 
                           username=session['username'])

# [Payment routes (M-Pesa/Binance) remain here as previously integrated]

if __name__ == '__main__':
    app.run(debug=True)