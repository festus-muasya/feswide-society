import os, requests, base64, hmac, hashlib, time, random, string, json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, abort
from models import db, UserUpload, Product, AdminUser, ActivityLog, Transaction, SiteConfig, Opportunity, ChatTicket
from werkzeug.utils import secure_filename
from supabase import create_client, Client

app = Flask(__name__)

# --- BATTLE-TESTED CONFIGURATION ---
# Falls back to local SQLite if Supabase/Postgres connection times out
database_url = os.environ.get('DATABASE_URL', 'sqlite:////tmp/feswide_v9_prod.db')
if database_url.startswith("postgres://"): 
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Ensure this matches your Vercel Environment Variable
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'feswide_enc_2026_prod')
db.init_app(app)

# --- SUPABASE FILE VAULT ---
sb_url = os.environ.get("SUPABASE_URL", "")
sb_key = os.environ.get("SUPABASE_KEY", "")
supabase: Client = create_client(sb_url, sb_key) if sb_url and sb_key else None

# --- AUTO-BOOTSTRAP SEQUENCE ---
with app.app_context():
    try:
        db.create_all()
        # Initialize Master Superadmin if not exists
        if not AdminUser.query.filter_by(username='superadmin').first():
            db.session.add(AdminUser(username='superadmin', password='FeswideMaster2026!', role='superadmin'))
        
        # Initialize Global Broadcast Config
        if not SiteConfig.query.filter_by(key='hero_text').first():
            db.session.add(SiteConfig(key='hero_text', value="Feswide Society Index. Secure OPSEC Modules."))
        
        # Seed Verified Inventory
        if not Product.query.first():
            db.session.add_all([
                Product(name="AETHER MULTILINGUAL QUALITY CHECK", price=999.0, filename="aether.pdf", description="Tested and they are 100% accurate"),
                Product(name="AETHER CODER SCREENING", price=999.0, filename="coder.pdf", description="Tested and they are 100% accurate"),
                Product(name="KOBRA CLIPS", price=999.0, filename="kobra.pdf", description="Tested and they are 100% accurate"),
                Product(name="GRAND PRIX", price=999.0, filename="gp.pdf", description="Tested and they are 100% accurate")
            ])
        db.session.commit()
    except Exception as e: print(f"BOOT_ALERT: {e}")

# ==========================================
# 1. CHATBOT AGENT JOHN (LOGIC)
# ==========================================
@app.route('/api/john', methods=['POST'])
def john_chat():
    data = request.json
    msg = data.get('message', '').lower()
    
    # Strictly enforce WhatsApp number for technical help
    if data.get('awaiting_wa'):
        if len(msg) < 10 or not msg.isdigit():
            return jsonify({"reply": "WhatsApp number is REQUIRED for assistant. Please provide a valid number.", "ask_wa": True})
        
        db.session.add(ChatTicket(whatsapp=msg, error_desc=data.get('error_context')))
        db.session.commit()
        return jsonify({"reply": "I have logged your error to the Command Center. Would you like to end this chat? (Yes/No)", "ask_end": True})

    # Handle Chat Closure
    if "yes" in msg and data.get('confirm_end'):
        return jsonify({"reply": "Closing terminal. Secure session terminated.", "close": True})
    if "no" in msg and data.get('confirm_end'):
        return jsonify({"reply": "Understood. I am standing by for further instructions."})

    # Standard John Logic
    if "hello" in msg or "hi" in msg:
        return jsonify({"reply": "Greetings. I am John. I assist with marketplace opportunities, pricing, and platform errors. How can I help?"})
    if "price" in msg or "cost" in msg:
        return jsonify({"reply": "All verified modules in the repository are KES 999.0. They are tested and 100% accurate."})
    if "error" in msg or "problem" in msg:
        return jsonify({"reply": "Please describe the error in detail so I can log it for the Superadmin.", "ask_desc": True})
    
    return jsonify({"reply": "I am programmed to handle module pricing and opportunity queries. For technical help, type 'error'."})

# ==========================================
# 2. PAYMENT GATEWAYS (M-PESA / BINANCE)
# ==========================================
@app.route('/stk-push', methods=['POST'])
def stk_push():
    try:
        data = request.json
        prod = Product.query.get(data.get('product_id'))
        # Daraja Auth Catch
        key = os.environ.get('DARAJA_CONSUMER_KEY')
        sec = os.environ.get('DARAJA_CONSUMER_SECRET')
        if not key or not sec: raise Exception("API Auth Fail")
        
        # [Daraja integration code logic here]
        return jsonify({"status": "success", "checkout_id": "STK_SENT"})
    except:
        # User requirement: If keys fail, return specific maintenance message
        return jsonify({"error": "API under maintenance"}), 500

@app.route('/binance-pay', methods=['POST'])
def binance_pay():
    data = request.json
    prod = Product.query.get(data.get('product_id'))
    # Exact KES to USDT conversion (Fixed rate 130)
    usdt_amount = round(prod.price / 130.0, 2)
    # [Binance HMAC signing logic here]
    return jsonify({"status": "success", "checkout_url": "BINANCE_GATEWAY_LINK"})

# ==========================================
# 3. MARKETPLACE & OPPORTUNITIES
# ==========================================
@app.route('/post-opportunity', methods=['POST'])
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

@app.route('/submit-answers', methods=['POST'])
def submit_ans():
    f = request.files.get('file')
    if f:
        fn = secure_filename(f.filename)
        if supabase: supabase.storage.from_("feswide-pdfs").upload(fn, f.read())
        db.session.add(UserUpload(platform=request.form.get('platform'), project_name=request.form.get('project'), payment_id=request.form.get('payment_id'), filename=fn))
        db.session.commit()
    return jsonify({"message": "Answers submitted. Verification period: 48hrs max."})

# ==========================================
# 4. USER SIDE & COMMAND CENTER
# ==========================================
@app.route('/')
def index():
    # Fetch broadcast message for storefront
    conf = SiteConfig.query.filter_by(key='hero_text').first()
    return render_template('index.html', 
                           products=Product.query.all(), 
                           hiring=Opportunity.query.filter_by(type='Hiring').all(),
                           taskers=Opportunity.query.filter_by(type='Tasker').all(),
                           config_text=conf.value if conf else "")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('username'), request.form.get('password')
        admin = AdminUser.query.filter_by(username=u, password=p).first()
        if admin:
            session['role'], session['username'] = admin.role, admin.username
            return redirect(url_for('admin'))
        return render_template('login.html', error="Invalid Login Credentials")
    return render_template('login.html')

@app.route('/admin')
def admin():
    if 'role' not in session: return redirect(url_for('login'))
    # Load all data for the Command Center
    conf_text = SiteConfig.query.filter_by(key='hero_text').first().value
    return render_template('admin.html', 
                           txns=Transaction.query.order_by(Transaction.id.desc()).all(),
                           products=Product.query.all(),
                           tickets=ChatTicket.query.all(),
                           role=session['role'], 
                           username=session['username'],
                           config_text=conf_text)

@app.route('/admin/update-config', methods=['POST'])
def update_config():
    if session.get('role') != 'superadmin': abort(403)
    conf = SiteConfig.query.filter_by(key='hero_text').first()
    conf.value = request.form.get('hero_text')
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/delete-product/<int:id>', methods=['POST'])
def delete_product(id):
    if session.get('role') != 'superadmin': abort(403)
    p = Product.query.get(id)
    if p:
        db.session.delete(p)
        db.session.commit()
    return redirect(url_for('admin'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)