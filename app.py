import os, requests, base64, hmac, hashlib, time, random, string, json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, abort
from models import db, UserUpload, Product, AdminUser, ActivityLog, Transaction, SiteConfig, Opportunity, ChatTicket
from werkzeug.utils import secure_filename
from supabase import create_client, Client

app = Flask(__name__)

# --- DATABASE & SECURITY CONFIG ---
database_url = os.environ.get('DATABASE_URL', 'sqlite:////tmp/feswide_v13_prod.db')
if database_url.startswith("postgres://"): 
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'feswide_enc_2026_prod')
db.init_app(app)

# --- SUPABASE FILE VAULT ---
sb_url = os.environ.get("SUPABASE_URL", "")
sb_key = os.environ.get("SUPABASE_KEY", "")
supabase: Client = create_client(sb_url, sb_key) if sb_url and sb_key else None

# --- AUTO-BOOTSTRAP ---
with app.app_context():
    try:
        db.create_all()
        if not AdminUser.query.filter_by(username='superadmin').first():
            db.session.add(AdminUser(username='superadmin', password='FeswideMaster2026!', role='superadmin'))
        if not SiteConfig.query.filter_by(key='hero_text').first():
            db.session.add(SiteConfig(key='hero_text', value="Feswide Society Index. Verified Modules."))
        
        if not Product.query.first():
            db.session.add_all([
                Product(name="AETHER MULTILINGUAL QUALITY CHECK", price=999.0, filename="aether.pdf", description="Tested and they are 100% accurate"),
                Product(name="AETHER CODER SCREENING", price=999.0, filename="coder.pdf", description="Tested and they are 100% accurate"),
                Product(name="KOBRA CLIPS", price=999.0, filename="kobra.pdf", description="Tested and they are 100% accurate"),
                Product(name="GRAND PRIX", price=999.0, filename="gp.pdf", description="Tested and they are 100% accurate")
            ])
        db.session.commit()
    except Exception as e: print(f"BOOT_ERROR: {e}")

# --- AGENT JOHN LOGIC ---
@app.route('/api/john', methods=['POST'])
def john_chat():
    data = request.json
    msg = data.get('message', '').lower()
    
    if data.get('awaiting_wa'):
        if len(msg) < 10 or not msg.isdigit():
            return jsonify({"reply": "WhatsApp number is REQUIRED for assistant. Please provide a valid number.", "ask_wa": True})
        db.session.add(ChatTicket(whatsapp=msg, error_desc=data.get('error_context')))
        db.session.commit()
        return jsonify({"reply": "Error logged. End chat? (Yes/No)", "ask_end": True})

    if "yes" in msg and data.get('confirm_end'): return jsonify({"reply": "Chat ended.", "close": True})
    if "no" in msg and data.get('confirm_end'): return jsonify({"reply": "Standing by. How else can I help?"})

    if "hello" in msg: return jsonify({"reply": "I am John. I assist with marketplace opportunities, pricing, and errors. How can I help?"})
    if "price" in msg: return jsonify({"reply": "Verified modules are KES 999.0. Tested and 100% accurate."})
    if "error" in msg: return jsonify({"reply": "Describe the error in detail.", "ask_desc": True})
    
    return jsonify({"reply": "I handle module pricing and marketplace queries. For technical help, type 'error'."})

# --- PAYMENT GATEWAYS ---
@app.route('/stk-push', methods=['POST'])
def stk_push():
    try:
        if not os.environ.get('DARAJA_CONSUMER_KEY'): raise Exception()
        return jsonify({"status": "success"})
    except:
        return jsonify({"error": "API under maintenance"}), 500

# --- MODERATION & ADMIN ---
@app.route('/admin/delete-opportunity/<int:id>', methods=['POST'])
def delete_opportunity(id):
    if session.get('role') != 'superadmin': abort(403)
    opp = Opportunity.query.get(id)
    if opp:
        db.session.delete(opp)
        db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/update-config', methods=['POST'])
def update_config():
    if session.get('role') != 'superadmin': abort(403)
    conf = SiteConfig.query.filter_by(key='hero_text').first()
    conf.value = request.form.get('hero_text')
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin')
def admin():
    if 'role' not in session: return redirect(url_for('login'))
    conf_obj = SiteConfig.query.filter_by(key='hero_text').first()
    return render_template('admin.html', 
                           txns=Transaction.query.order_by(Transaction.id.desc()).all(),
                           products=Product.query.all(),
                           hiring=Opportunity.query.filter_by(type='Hiring').all(),
                           taskers=Opportunity.query.filter_by(type='Tasker').all(),
                           tickets=ChatTicket.query.all(),
                           role=session['role'], 
                           username=session['username'],
                           config_text=conf_obj.value if conf_obj else "")

# --- PUBLIC ROUTES ---
@app.route('/')
def index():
    conf = SiteConfig.query.filter_by(key='hero_text').first()
    return render_template('index.html', 
                           products=Product.query.all(), 
                           hiring=Opportunity.query.filter_by(type='Hiring').all(),
                           taskers=Opportunity.query.filter_by(type='Tasker').all(),
                           config_text=conf.value if conf else "")

@app.route('/post-opportunity', methods=['POST'])
def post_opp():
    db.session.add(Opportunity(type=request.form.get('type'), platform=request.form.get('platform'), rate=request.form.get('rate'), whatsapp=request.form.get('whatsapp'), description=request.form.get('desc')))
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('username'), request.form.get('password')
        admin = AdminUser.query.filter_by(username=u, password=p).first()
        if admin:
            session['role'], session['username'] = admin.role, admin.username
            return redirect(url_for('admin'))
        return render_template('login.html', error="Invalid Access Credentials")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)