import os, json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, abort
from models import db, UserUpload, Product, AdminUser, ActivityLog, Transaction, SiteConfig, Opportunity, ChatTicket
from werkzeug.utils import secure_filename
from supabase import create_client, Client

app = Flask(__name__)

# --- DATABASE & SECURITY CONFIG ---
database_url = os.environ.get('DATABASE_URL', 'sqlite:////tmp/feswide_v23_master.db')
if database_url.startswith("postgres://"): 
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'feswide_enc_2026_prod')

# OPSEC: Session Hardening
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True

db.init_app(app)

# --- SUPABASE FILE VAULT ---
supabase: Client = create_client(os.environ.get("SUPABASE_URL", ""), os.environ.get("SUPABASE_KEY", "")) if os.environ.get("SUPABASE_URL") else None

# --- AUTO-BOOTSTRAP SEQUENCE ---
with app.app_context():
    try:
        db.create_all()
        # Initialize Superadmin
        if not AdminUser.query.filter_by(username='superadmin').first():
            db.session.add(AdminUser(username='superadmin', password='FeswideMaster2026!', role='superadmin'))
        
        # Initialize Broadcast Config
        if not SiteConfig.query.filter_by(key='hero_text').first():
            db.session.add(SiteConfig(key='hero_text', value="Feswide Society: Secure your edge with verified trajectories."))
        
        # Seed Full Document Repository
        if not Product.query.first():
            db.session.add_all([
                Product(name="GRAND PRIX", price=999.0, filename="gp.pdf", description="Verified expert-level trajectories."),
                Product(name="BLACKBEARD", price=999.0, filename="bb.pdf", description="Tested 100% accurate solutions."),
                Product(name="CACATUA CHORUS", price=999.0, filename="cc.pdf", description="PhD-level quality checked answers."),
                Product(name="WHITE CLAW", price=999.0, filename="wc.pdf", description="Official accuracy verified."),
                Product(name="AETHER QUALITY CHECK", price=999.0, filename="aether.pdf", description="Multilingual standard trajectories."),
                Product(name="KOBRA CLIPS", price=999.0, filename="kobra.pdf", description="Adversarial prompt mastery.")
            ])
        db.session.commit()
    except Exception as e: print(f"BOOT_ERROR: {e}")

# ==========================================
# 1. PUBLIC NAVIGATION
# ==========================================

@app.route('/')
def index():
    conf = SiteConfig.query.filter_by(key='hero_text').first()
    return render_template('index.html', products=Product.query.all(), config_text=conf.value if conf else "")

@app.route('/opportunities')
def opportunities_page():
    """Renders the dedicated marketplace page"""
    return render_template('opportunities.html', 
                           hiring=Opportunity.query.filter_by(type='Hiring').all(),
                           taskers=Opportunity.query.filter_by(type='Tasker').all())

# ==========================================
# 2. MARKETPLACE & REWARDS
# ==========================================

@app.route('/submit-answers', methods=['POST'])
def submit_ans():
    try:
        f = request.files.get('file')
        if not f: return jsonify({"error": "No file uploaded"}), 400
        fn = secure_filename(f.filename)
        if supabase: supabase.storage.from_("feswide-pdfs").upload(fn, f.read())
        db.session.add(UserUpload(platform=request.form.get('platform'), project_name=request.form.get('project'), payment_id=request.form.get('payment_id'), filename=fn))
        db.session.commit()
        return jsonify({"message": "Submission Successful! 48hr review started."}), 200
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/post-opportunity', methods=['POST'])
def post_opp():
    db.session.add(Opportunity(type=request.form.get('type'), platform=request.form.get('platform'), rate=request.form.get('rate'), whatsapp=request.form.get('whatsapp'), description=request.form.get('desc')))
    db.session.commit()
    return redirect(url_for('opportunities_page'))

# ==========================================
# 3. AGENT JOHN (MODERN UI LOGIC)
# ==========================================

@app.route('/api/john', methods=['POST'])
def john_chat():
    data = request.json
    msg = data.get('message', '').lower()
    if data.get('awaiting_wa'):
        if len(msg) < 10 or not msg.isdigit(): return jsonify({"reply": "Valid WhatsApp required.", "ask_wa": True})
        db.session.add(ChatTicket(whatsapp=msg, error_desc=data.get('error_context')))
        db.session.commit()
        return jsonify({"reply": "Logged. End session? (Yes/No)", "ask_end": True})
    if "yes" in msg and data.get('confirm_end'): return jsonify({"reply": "Closing...", "close": True})
    if "error" in msg: return jsonify({"reply": "Describe issue.", "ask_desc": True})
    return jsonify({"reply": "I am John. How can I help?"})

# ==========================================
# 4. SUPERADMIN COMMAND CENTER
# ==========================================

@app.route('/admin')
def admin():
    if 'role' not in session: return redirect(url_for('login'))
    conf = SiteConfig.query.filter_by(key='hero_text').first()
    return render_template('admin.html', 
                           admins=AdminUser.query.all(),
                           products=Product.query.all(),
                           txns=Transaction.query.order_by(Transaction.id.desc()).all(),
                           submissions=UserUpload.query.order_by(UserUpload.id.desc()).all(),
                           hiring=Opportunity.query.filter_by(type='Hiring').all(),
                           taskers=Opportunity.query.filter_by(type='Tasker').all(),
                           tickets=ChatTicket.query.all(),
                           role=session['role'], 
                           username=session['username'],
                           config_text=conf.value if conf else "")

@app.route('/admin/add-subadmin', methods=['POST'])
def add_subadmin():
    if session.get('role') != 'superadmin': abort(403)
    db.session.add(AdminUser(username=request.form.get('u'), password=request.form.get('p'), role='subadmin'))
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/del-user/<int:id>')
def del_user(id):
    if session.get('role') != 'superadmin': abort(403)
    AdminUser.query.filter_by(id=id).delete(); db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/add-product', methods=['POST'])
def add_product():
    if session.get('role') != 'superadmin': abort(403)
    db.session.add(Product(name=request.form.get('n').upper(), price=float(request.form.get('pr')), filename=request.form.get('fn')))
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/del-product/<int:id>')
def del_product(id):
    if session.get('role') != 'superadmin': abort(403)
    Product.query.filter_by(id=id).delete(); db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/update-config', methods=['POST'])
def update_config():
    if session.get('role') != 'superadmin': abort(403)
    conf = SiteConfig.query.filter_by(key='hero_text').first()
    conf.value = request.form.get('hero_text'); db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/delete-opportunity/<int:id>', methods=['POST'])
def delete_opportunity(id):
    if session.get('role') != 'superadmin': abort(403)
    Opportunity.query.filter_by(id=id).delete(); db.session.commit()
    return redirect(url_for('admin'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        admin_user = AdminUser.query.filter_by(username=request.form.get('username'), password=request.form.get('password')).first()
        if admin_user:
            session['role'], session['username'] = admin_user.role, admin_user.username
            return redirect(url_for('admin'))
        return render_template('login.html', error="Access Denied.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('index'))

@app.route('/stk-push', methods=['POST'])
def stk_push():
    # Logic to log transaction attempt
    db.session.add(Transaction(checkout_request_id="REQ_"+str(datetime.now().timestamp()), phone=request.json.get('phone'), amount=999.0, status="Failed (Keys Missing)"))
    db.session.commit()
    return jsonify({"error": "API under maintenance"}), 500

if __name__ == '__main__':
    app.run(debug=True)