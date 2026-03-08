import os, requests, base64, hmac, hashlib, time, random, string, json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, abort
from models import db, UserUpload, Product, AdminUser, ActivityLog, Transaction, SiteConfig, Opportunity, ChatTicket
from werkzeug.utils import secure_filename

app = Flask(__name__)

# --- DATABASE & SECURITY CONFIG ---
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:////tmp/feswide_v14_prod.db').replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'feswide_enc_2026_prod')
db.init_app(app)

with app.app_context():
    db.create_all()
    if not AdminUser.query.filter_by(username='superadmin').first():
        db.session.add(AdminUser(username='superadmin', password='FeswideMaster2026!', role='superadmin'))
    if not SiteConfig.query.filter_by(key='hero_text').first():
        db.session.add(SiteConfig(key='hero_text', value="Feswide Society Index. Verified Modules."))
    db.session.commit()

# --- CHATBOT JOHN LOGIC ---
@app.route('/api/john', methods=['POST'])
def john_chat():
    data = request.json
    msg = data.get('message', '').lower()
    
    if data.get('awaiting_wa'):
        if len(msg) < 10 or not msg.isdigit():
            return jsonify({"reply": "WhatsApp number is REQUIRED for assistant. Please provide a valid number.", "ask_wa": True})
        db.session.add(ChatTicket(whatsapp=msg, error_desc=data.get('error_context')))
        db.session.commit()
        return jsonify({"reply": "I have logged your error. Would you like to end this chat? (Yes/No)", "ask_end": True})

    if "yes" in msg and data.get('confirm_end'): return jsonify({"reply": "Chat ended.", "close": True})
    if "no" in msg and data.get('confirm_end'): return jsonify({"reply": "Standing by. How else can I help?"})
    if "error" in msg: return jsonify({"reply": "Please describe the error clearly.", "ask_desc": True})
    return jsonify({"reply": "I am John. How can I assist with modules or opportunities?"})

# --- PAYMENT GATEWAY MONITOR ---
@app.route('/stk-push', methods=['POST'])
def stk_push():
    try:
        # Check for active API keys
        if not os.environ.get('DARAJA_CONSUMER_KEY'): raise Exception()
        # [Daraja STK Logic]
        return jsonify({"status": "success"})
    except:
        return jsonify({"error": "API under maintenance"}), 500

# --- MODERATION & MARKETPLACE ---
@app.route('/admin/delete-opportunity/<int:id>', methods=['POST'])
def delete_opportunity(id):
    if session.get('role') != 'superadmin': abort(403)
    opp = Opportunity.query.get(id)
    if opp: db.session.delete(opp); db.session.commit()
    return redirect(url_for('admin'))

@app.route('/post-opportunity', methods=['POST'])
def post_opp():
    db.session.add(Opportunity(type=request.form.get('type'), platform=request.form.get('platform'), rate=request.form.get('rate'), whatsapp=request.form.get('whatsapp'), description=request.form.get('desc')))
    db.session.commit()
    return redirect(url_for('index'))

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
    conf = SiteConfig.query.filter_by(key='hero_text').first()
    return render_template('admin.html', txns=Transaction.query.all(), products=Product.query.all(), hiring=Opportunity.query.filter_by(type='Hiring').all(), taskers=Opportunity.query.filter_by(type='Tasker').all(), tickets=ChatTicket.query.all(), role=session['role'], username=session['username'], config_text=conf.value if conf else "")

@app.route('/admin/update-config', methods=['POST'])
def update_config():
    if session.get('role') != 'superadmin': abort(403)
    conf = SiteConfig.query.filter_by(key='hero_text').first()
    conf.value = request.form.get('hero_text')
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('username'), request.form.get('password')
        admin = AdminUser.query.filter_by(username=u, password=p).first()
        if admin: session['role'], session['username'] = admin.role, admin.username; return redirect(url_for('admin'))
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True)