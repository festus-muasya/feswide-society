import os, requests, base64
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, abort
from models import db, UserUpload, Product, ProjectRequest, AdminUser, ActivityLog, Transaction, SiteConfig
from werkzeug.utils import secure_filename
from supabase import create_client, Client

app = Flask(__name__)

# --- CONFIG & DATABASE ---
database_url = os.environ.get('DATABASE_URL', 'sqlite:////tmp/feswide.db')
if database_url.startswith("postgres://"): 
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'feswide_global_2026')
db.init_app(app)

# --- SUPABASE STORAGE CONFIG ---
# (Note: These are different from DATABASE_URL. These handle PDF file uploads)
sb_url = os.environ.get("SUPABASE_URL", "")
sb_key = os.environ.get("SUPABASE_KEY", "")
supabase: Client = create_client(sb_url, sb_key) if sb_url and sb_key else None

def log_action(operator, action):
    try:
        db.session.add(ActivityLog(operator=operator, action=action))
        db.session.commit()
    except Exception as e:
        print(f"Log Error: {e}")

# ANTI-CRASH BOOT SEQUENCE
with app.app_context():
    try:
        db.create_all()
        if not AdminUser.query.first():
            db.session.add(AdminUser(username='superadmin', password='FeswideMaster2026!', role='superadmin'))
        if not SiteConfig.query.filter_by(key='hero_text').first():
            db.session.add(SiteConfig(key='hero_text', value="Feswide Society Index. Secure OPSEC Modules."))
        db.session.commit()
        print("DATABASE SYNCED SUCCESSFULLY.")
    except Exception as e:
        print(f"CRITICAL DATABASE ERROR ON BOOT: {e}")

# --- M-PESA & PAYMENT ROUTING ---
def get_daraja_token():
    key = os.environ.get('DARAJA_CONSUMER_KEY', '').strip()
    secret = os.environ.get('DARAJA_CONSUMER_SECRET', '').strip()
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials" 
    try:
        credentials = base64.b64encode(f"{key}:{secret}".encode()).decode('utf-8')
        r = requests.get(url, headers={"Authorization": f"Basic {credentials}"}, timeout=15)
        return r.json().get('access_token'), None if r.status_code == 200 else r.text
    except Exception as e: 
        return None, str(e)

@app.route('/stk-push', methods=['POST'])
def stk_push():
    try:
        data = request.json
        phone, product_id = data.get('phone'), data.get('product_id')
        product = Product.query.get(product_id)
        
        token, err = get_daraja_token()
        if not token: 
            return jsonify({"error": f"Safaricom Auth Failed: {err}"}), 500

        shortcode = os.environ.get('DARAJA_BUSINESS_SHORTCODE', '174379').strip()
        passkey = os.environ.get('DARAJA_PASSKEY', 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919').strip()
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password = base64.b64encode((shortcode + passkey + timestamp).encode()).decode('utf-8')

        if phone.startswith('0'): phone = '254' + phone[1:]
        
        cb_url = request.host_url.rstrip('/') + "/daraja-callback"
        cb_url = cb_url.replace("http://", "https://") if "localhost" not in cb_url else cb_url

        payload = {
            "BusinessShortCode": shortcode, "Password": password, "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline", "Amount": 1, 
            "PartyA": phone, "PartyB": shortcode, "PhoneNumber": phone,
            "CallBackURL": cb_url, "AccountReference": f"FW_{product.id}", "TransactionDesc": "Feswide Module"
        }

        r = requests.post("https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest", json=payload, headers={"Authorization": f"Bearer {token}"}, timeout=15)
        res = r.json()
        
        if res.get('ResponseCode') == '0':
            db.session.add(Transaction(checkout_request_id=res.get('CheckoutRequestID'), phone=phone, amount=1, product_id=product.id, ip_address=request.remote_addr))
            db.session.commit()
            return jsonify({"status": "success", "checkout_id": res.get('CheckoutRequestID')})
            
        return jsonify({"error": res.get('errorMessage', 'Failed to trigger STK')}), 400
    except Exception as e: 
        return jsonify({"error": str(e)}), 500

@app.route('/verify-manual', methods=['POST'])
def verify_manual():
    try:
        data = request.json
        db.session.add(Transaction(checkout_request_id=data.get('txn_id'), phone="AIRTEL", amount=999, product_id=data.get('product_id'), status='Pending Manual', ip_address=request.remote_addr))
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/daraja-callback', methods=['POST'])
def daraja_callback():
    try:
        body = request.get_json().get('Body', {}).get('stkCallback', {})
        txn = Transaction.query.filter_by(checkout_request_id=body.get('CheckoutRequestID')).first()
        if txn:
            txn.status = 'Paid' if body.get('ResultCode') == 0 else 'Failed'
            db.session.commit()
    except Exception: pass
    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})

@app.route('/check-payment/<checkout_id>')
def check_payment(checkout_id):
    try:
        txn = Transaction.query.filter_by(checkout_request_id=checkout_id).first()
        if txn and txn.status == 'Paid': 
            return jsonify({"status": "Paid", "download_token": txn.download_token})
        return jsonify({"status": txn.status if txn else "Pending"})
    except Exception:
        return jsonify({"status": "Error"})

@app.route('/secure-download/<token>')
def secure_download(token):
    try:
        txn = Transaction.query.filter_by(download_token=token).first()
        if not txn or txn.status != 'Paid': abort(403)
        
        if txn.ip_address and txn.ip_address != request.remote_addr:
            return "SECURITY BREACH DETECTED: IP Address mismatch. Link invalidated.", 403
        if txn.download_count >= 3: 
            return "ACCESS DENIED: Download limit reached.", 403
        
        product = Product.query.get(txn.product_id)
        txn.download_count += 1
        db.session.commit()
        
        if supabase:
            res = supabase.storage.from_('feswide-pdfs').create_signed_url(product.filename, 60)
            return redirect(res['signedURL'])
        return "Storage Error: Supabase File Bucket not linked.", 500
    except Exception as e:
        return f"Download Error: {e}", 500

# --- USER ROUTES ---
@app.route('/')
def index():
    try:
        config = {c.key: c.value for c in SiteConfig.query.all()}
        products = Product.query.all()
    except Exception as e:
        print(f"DB READ ERROR ON HOMEPAGE: {e}")
        config = {'hero_text': 'DATABASE OFFLINE. CHECK LOGS.'}
        products = []
    return render_template('index.html', products=products, config=config)

@app.route('/upload-answer', methods=['POST'])
def upload_answer():
    file = request.files.get('file')
    if file and file.filename.endswith('.pdf'):
        fname = secure_filename(file.filename)
        if supabase:
            file_bytes = file.read()
            supabase.storage.from_("feswide-pdfs").upload(fname, file_bytes)
            try:
                db.session.add(UserUpload(platform=request.form.get('platform'), project_name=request.form.get('project_name'), mpesa_number=request.form.get('mpesa_number'), filename=fname))
                db.session.commit()
            except Exception: pass
            return jsonify({"status": "success", "message": "Uploaded securely to Supabase."})
        return jsonify({"status": "error", "message": "Supabase File Storage not configured."}), 500
    return jsonify({"status": "error", "message": "Invalid file. PDFs only."}), 400

@app.route('/api/chat', methods=['POST'])
def faith_chat():
    return jsonify({"reply": "I am Agent Faith. Contact support@feswide.com for secure handling."})

# --- ADMIN ROUTES ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            u, p = request.form.get('username'), request.form.get('password')
            admin_user = AdminUser.query.filter_by(username=u, password=p).first()
            if admin_user and admin_user.is_active:
                session['role'], session['username'] = admin_user.role, admin_user.username
                log_action(u, "Terminal Access Granted")
                return redirect(url_for('admin'))
            return render_template('login.html', error="ACCESS DENIED.")
        except Exception as e:
            return render_template('login.html', error=f"DATABASE ERROR: {e}")
    return render_template('login.html')

@app.route('/admin')
def admin():
    if 'role' not in session: return redirect(url_for('login'))
    try:
        config = {c.key: c.value for c in SiteConfig.query.all()}
        return render_template('admin.html', 
                               uploads=UserUpload.query.order_by(UserUpload.id.desc()).all(), 
                               products=Product.query.all(),
                               txns=Transaction.query.order_by(Transaction.id.desc()).all(),
                               admins=AdminUser.query.all() if session['role'] == 'superadmin' else [],
                               logs=ActivityLog.query.order_by(ActivityLog.id.desc()).limit(50).all(),
                               role=session['role'], username=session['username'], config=config)
    except Exception as e:
        return f"Admin Terminal Database Error: {e}"

@app.route('/admin/approve-manual/<int:id>', methods=['POST'])
def approve_manual(id):
    if session.get('role') not in ['superadmin', 'subadmin']: abort(403)
    try:
        txn = Transaction.query.get_or_404(id)
        txn.status = 'Paid'
        db.session.commit()
        log_action(session['username'], f"Manually approved Airtel TXN: {txn.checkout_request_id}")
    except Exception: pass
    return jsonify({"success": True})

@app.route('/admin/update-config', methods=['POST'])
def update_config():
    if session.get('role') != 'superadmin': abort(403)
    try:
        for key, value in request.form.items():
            conf = SiteConfig.query.filter_by(key=key).first()
            if conf: conf.value = value
        db.session.commit()
    except Exception: pass
    return redirect(url_for('admin'))

@app.route('/admin/create-subadmin', methods=['POST'])
def create_subadmin():
    if session.get('role') != 'superadmin': abort(403)
    try:
        u, p = request.form.get('username'), request.form.get('password')
        if not AdminUser.query.filter_by(username=u).first():
            db.session.add(AdminUser(username=u, password=p, role='subadmin'))
            db.session.commit()
    except Exception: pass
    return redirect(url_for('admin'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)