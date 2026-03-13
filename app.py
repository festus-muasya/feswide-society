import os, requests, base64, hmac, hashlib, time, random, string, json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, abort
from models import db, UserUpload, Product, AdminUser, ActivityLog, Transaction, SiteConfig, Opportunity, ChatTicket
from werkzeug.utils import secure_filename
from supabase import create_client, Client

app = Flask(__name__)

# --- DATABASE & SECURITY CONFIG ---
# Prioritizes your PostgreSQL/Supabase URL for Vercel deployment.
database_url = os.environ.get('DATABASE_URL', 'sqlite:////tmp/feswide_v19_final.db')
if database_url.startswith("postgres://"): 
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'feswide_enc_2026_prod')
db.init_app(app)

# --- SUPABASE FILE VAULT ---
supabase: Client = create_client(os.environ.get("SUPABASE_URL", ""), os.environ.get("SUPABASE_KEY", "")) if os.environ.get("SUPABASE_URL") else None

# --- AUTO-BOOTSTRAP SEQUENCE ---
with app.app_context():
    try:
        db.create_all()
        
        # 1. Initialize Master Superadmin
        if not AdminUser.query.filter_by(username='superadmin').first():
            db.session.add(AdminUser(username='superadmin', password='FeswideMaster2026!', role='superadmin'))
        
        # 2. Initialize Global Broadcast Alert (Prefix-free)
        if not SiteConfig.query.filter_by(key='hero_text').first():
            db.session.add(SiteConfig(key='hero_text', value="Secure your edge with verified trajectories. 100% accuracy guaranteed."))
        
        # 3. Seed Updated Inventory (Grand Prix, Blackbeard, etc.)
        if not Product.query.first():
            db.session.add_all([
                Product(name="GRAND PRIX", price=999.0, filename="grand_prix.pdf", description="Verified expert-level trajectories."),
                Product(name="BLACKBEARD", price=999.0, filename="blackbeard.pdf", description="Tested and 100% accurate solutions."),
                Product(name="CACATUA CHORUS", price=999.0, filename="cacatua.pdf", description="PhD-level quality checked answers."),
                Product(name="WHITE CLAW", price=999.0, filename="white_claw.pdf", description="Verified verified trajectories for elite taskers.")
            ])
        db.session.commit()
    except Exception as e: 
        print(f"BOOT_ERROR: {e}")

# ==========================================
# 1. AGENT JOHN SUPPORT LOGIC
# ==========================================
@app.route('/api/john', methods=['POST'])
def john_chat():
    data = request.json
    msg = data.get('message', '').lower()
    
    # Strictly enforce WhatsApp number for technical support tickets
    if data.get('awaiting_wa'):
        if len(msg) < 10 or not msg.isdigit():
            return jsonify({"reply": "WhatsApp number is REQUIRED for assistant. Please provide a valid number.", "ask_wa": True})
        
        db.session.add(ChatTicket(whatsapp=msg, error_desc=data.get('error_context')))
        db.session.commit()
        return jsonify({"reply": "I have logged your error to the Command Center. Would you like to end this chat? (Yes/No)", "ask_end": True})

    # Session Closure Logic
    if "yes" in msg and data.get('confirm_end'):
        return jsonify({"reply": "Closing John Assistant terminal.", "close": True})
    if "no" in msg and data.get('confirm_end'):
        return jsonify({"reply": "Understood. How else can I assist you today?"})

    # Standard Conversation
    if "hello" in msg or "hi" in msg:
        return jsonify({"reply": "I am John. I assist with marketplace opportunities, pricing, and platform errors. How can I help?"})
    if "price" in msg or "cost" in msg:
        return jsonify({"reply": "All verified trajectories are KES 999.0. They are tested and 100% accurate."})
    if "error" in msg or "problem" in msg:
        return jsonify({"reply": "Please describe the error in detail so I can log it for the Superadmin.", "ask_desc": True})
    
    return jsonify({"reply": "I handle pricing and marketplace queries. For technical help, type 'error'."})

# ==========================================
# 2. PAYMENT GATEWAYS
# ==========================================
@app.route('/stk-push', methods=['POST'])
def stk_push():
    try:
        # Check for active Daraja API keys
        if not os.environ.get('DARAJA_CONSUMER_KEY'): 
            raise Exception("API Keys Not Set")
        # [Daraja STK Logic goes here]
        return jsonify({"status": "success", "checkout_id": "STK_SENT"})
    except:
        # Returns specific maintenance message as requested
        return jsonify({"error": "API under maintenance"}), 500

# ==========================================
# 3. MODERATION & MARKETPLACE
# ==========================================
@app.route('/admin/delete-opportunity/<int:id>', methods=['POST'])
def delete_opportunity(id):
    """Allows Superadmins to remove Tasker/Hiring posts from the dashboard"""
    if session.get('role') != 'superadmin': 
        abort(403)
    opp = Opportunity.query.get(id)
    if opp:
        db.session.delete(opp)
        db.session.commit()
    return redirect(url_for('admin'))

@app.route('/post-opportunity', methods=['POST'])
def post_opp():
    db.session.add(Opportunity(
        type=request.form.get('type'), 
        platform=request.form.get('platform'), 
        rate=request.form.get('rate'), 
        whatsapp=request.form.get('whatsapp'), 
        description=request.form.get('desc')
    ))
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/submit-answers', methods=['POST'])
def submit_ans():
    """Handles the 'Get Paid' submission flow for users"""
    try:
        f = request.files.get('file')
        if not f: return jsonify({"error": "No file uploaded"}), 400
        
        fn = secure_filename(f.filename)
        if supabase: 
            supabase.storage.from_("feswide-pdfs").upload(fn, f.read())
            
        db.session.add(UserUpload(
            platform=request.form.get('platform'), 
            project_name=request.form.get('project'), 
            payment_id=request.form.get('payment_id'), 
            filename=fn
        ))
        db.session.commit()
        return jsonify({"message": "Submission Successful! 48hr review started."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# 4. ADMIN & PUBLIC NAVIGATION
# ==========================================
@app.route('/admin')
def admin():
    if 'role' not in session: return redirect(url_for('login'))
    conf = SiteConfig.query.filter_by(key='hero_text').first()
    return render_template('admin.html', 
                           txns=Transaction.query.order_by(Transaction.id.desc()).all(),
                           products=Product.query.all(),
                           hiring=Opportunity.query.filter_by(type='Hiring').all(),
                           taskers=Opportunity.query.filter_by(type='Tasker').all(),
                           tickets=ChatTicket.query.all(),
                           role=session['role'], 
                           username=session['username'],
                           config_text=conf.value if conf else "")

@app.route('/admin/update-config', methods=['POST'])
def update_config():
    if session.get('role') != 'superadmin': abort(403)
    conf = SiteConfig.query.filter_by(key='hero_text').first()
    conf.value = request.form.get('hero_text')
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/')
def index():
    # Site Hero Text broadcast
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

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)