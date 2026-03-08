import os, requests, base64
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, session, abort
from models import db, UserUpload, Product, ProjectRequest, AdminUser, ActivityLog, Transaction, SiteConfig
from werkzeug.utils import secure_filename

app = Flask(__name__, instance_path='/tmp/instance')

# --- CONFIGURATION & DATABASE ---
database_url = os.environ.get('DATABASE_URL', 'sqlite:////tmp/feswide.db')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'feswide_global_secure_2026')

# Vercel Read-Only File System Fix
UPLOAD_DIR = '/tmp/uploads' if os.environ.get('VERCEL_ENV') else os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

db.init_app(app)

def log_action(operator, action):
    db.session.add(ActivityLog(operator=operator, action=action))
    db.session.commit()

with app.app_context():
    db.create_all()
    # Seed default products with IDENTICAL descriptions and 999 pricing
    standard_desc = "Verified Feswide Golden Trajectory answers. Secure download restricted to buyer."
    if not Product.query.first():
        db.session.add_all([
            Product(name="Aether Multilingual Quality Check", price=999.0, filename="aether.pdf", description=standard_desc),
            Product(name="Aether Coder Screening", price=999.0, filename="coder.pdf", description=standard_desc),
            Product(name="Kobra Clips", price=999.0, filename="kobra.pdf", description=standard_desc),
            Product(name="Grand Prix", price=999.0, filename="gp.pdf", description=standard_desc)
        ])
    if not SiteConfig.query.filter_by(key='hero_text').first():
        db.session.add(SiteConfig(key='hero_text', value="Welcome to the Feswide Society Index. All available AI training modules are rigorously verified by our Quality Assurance team."))
    if not SiteConfig.query.filter_by(key='upload_notice').first():
        db.session.add(SiteConfig(key='upload_notice', value="Requirement: Submit your completed PDF for review. Approved submissions generate a KES 500 payout to the provided M-Pesa number."))
    db.session.commit()

# --- M-PESA DARAJA INTEGRATION ---
def get_daraja_token():
    # .strip() prevents hidden space errors from Vercel env variables
    key = os.environ.get('DARAJA_CONSUMER_KEY', '').strip()
    secret = os.environ.get('DARAJA_CONSUMER_SECRET', '').strip()
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials" 
    
    try:
        r = requests.get(url, auth=(key, secret), timeout=10)
        if r.status_code == 200:
            return r.json().get('access_token')
        else:
            print(f"DARAJA AUTH REJECTED: Status {r.status_code} - {r.text}")
            return None
    except Exception as e: 
        print(f"DARAJA NETWORK ERROR: {e}")
        return None

@app.route('/stk-push', methods=['POST'])
def stk_push():
    data = request.json
    phone = data.get('phone')
    product_id = data.get('product_id')
    
    product = Product.query.get(product_id)
    if not product or not phone: return jsonify({"error": "Invalid request"}), 400

    token = get_daraja_token()
    if not token: 
        return jsonify({"error": "Payment Gateway Error. Check Vercel logs."}), 500

    shortcode = os.environ.get('DARAJA_BUSINESS_SHORTCODE', '174379').strip()
    passkey = os.environ.get('DARAJA_PASSKEY', 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919').strip()
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = base64.b64encode((shortcode + passkey + timestamp).encode()).decode('utf-8')

    # Format phone to 254...
    if phone.startswith('0'): phone = '254' + phone[1:]
    elif phone.startswith('+'): phone = phone[1:]

    headers = {"Authorization": f"Bearer {token}"}
    
    # Ensure Callback URL is an absolute HTTPS link
    callback_url = request.host_url.rstrip('/') + "/daraja-callback"
    if callback_url.startswith("http://") and "localhost" not in callback_url:
        callback_url = callback_url.replace("http://", "https://")

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(product.price),
        "PartyA": phone,
        "PartyB": shortcode,
        "PhoneNumber": phone,
        "CallBackURL": callback_url,
        "AccountReference": f"Feswide_{product.id}",
        "TransactionDesc": f"Payment for {product.name}"
    }

    url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest" 
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        response_data = r.json()

        if response_data.get('ResponseCode') == '0':
            checkout_id = response_data.get('CheckoutRequestID')
            db.session.add(Transaction(checkout_request_id=checkout_id, phone=phone, amount=product.price, product_id=product.id))
            db.session.commit()
            return jsonify({"status": "success", "checkout_id": checkout_id})
        else:
            print(f"STK PUSH FAILED: {response_data}")
            return jsonify({"error": "Failed to trigger M-Pesa. Check number format or Daraja balance."}), 400
    except Exception as e:
        print(f"STK PUSH EXCEPTION: {e}")
        return jsonify({"error": "M-Pesa API connection failed."}), 500

@app.route('/daraja-callback', methods=['POST'])
def daraja_callback():
    data = request.get_json()
    try:
        body = data.get('Body', {}).get('stkCallback', {})
        checkout_id = body.get('CheckoutRequestID')
        result_code = body.get('ResultCode')
        
        txn = Transaction.query.filter_by(checkout_request_id=checkout_id).first()
        if txn:
            txn.status = 'Paid' if result_code == 0 else 'Failed'
            db.session.commit()
    except Exception as e: 
        print(f"CALLBACK ERROR: {e}")
    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})

@app.route('/check-payment/<checkout_id>')
def check_payment(checkout_id):
    txn = Transaction.query.filter_by(checkout_request_id=checkout_id).first()
    if txn and txn.status == 'Paid':
        return jsonify({"status": "Paid", "download_token": txn.download_token})
    return jsonify({"status": txn.status if txn else "Pending"})

@app.route('/secure-download/<token>')
def secure_download(token):
    txn = Transaction.query.filter_by(download_token=token).first()
    if not txn or txn.status != 'Paid': abort(403)
    if txn.download_count >= 3: return "ACCESS DENIED: This secure download link has expired.", 403
    
    product = Product.query.get(txn.product_id)
    txn.download_count += 1
    db.session.commit()
    return send_from_directory(UPLOAD_DIR, product.filename, as_attachment=True)

# --- USER ROUTES ---
@app.route('/')
def index():
    config = {c.key: c.value for c in SiteConfig.query.all()}
    return render_template('index.html', products=Product.query.all(), config=config)

@app.route('/upload-answer', methods=['POST'])
def upload_answer():
    file = request.files.get('file')
    if file and file.filename.endswith('.pdf'):
        fname = secure_filename(file.filename)
        file.save(os.path.join(UPLOAD_DIR, fname))
        db.session.add(UserUpload(platform=request.form.get('platform'), project_name=request.form.get('project_name'), mpesa_number=request.form.get('mpesa_number'), filename=fname))
        db.session.commit()
        return jsonify({"status": "success", "message": "Upload successful. Manual review initiated."})
    return jsonify({"status": "error", "message": "Only PDF format is accepted."}), 400

@app.route('/request-project', methods=['POST'])
def request_project():
    data = request.json
    db.session.add(ProjectRequest(project_name=data.get('project_name'), platform=data.get('platform')))
    db.session.commit()
    return jsonify({"status": "success", "message": "Request logged successfully."})

@app.route('/api/chat', methods=['POST'])
def faith_chat():
    msg = request.json.get('message', '').lower()
    if any(w in msg for w in ["hi", "hello"]): reply = "Hello. I am Agent Faith. How can I assist you today?"
    elif "price" in msg: reply = "Premium modules are KES 999. Contributors earn KES 500 per approved PDF."
    elif "upload" in msg: reply = "Securely upload Handshake or Outlier PDFs via the Contributor Hub."
    else: reply = "Processing request. Contact support@feswide.com for human assistance."
    return jsonify({"reply": reply})

# --- ADMIN ROUTES ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if not AdminUser.query.first():
        db.session.add(AdminUser(username='superadmin', password='FeswideMaster2026!', role='superadmin'))
        db.session.commit()

    if request.method == 'POST':
        u, p = request.form.get('username'), request.form.get('password')
        admin_user = AdminUser.query.filter_by(username=u, password=p).first()
        if admin_user:
            if not admin_user.is_active: return render_template('login.html', error="ACCOUNT SUSPENDED.")
            session['role'], session['username'] = admin_user.role, admin_user.username
            log_action(u, "Logged into Terminal")
            return redirect(url_for('admin'))
        return render_template('login.html', error="INVALID CREDENTIALS.")
    return render_template('login.html')

@app.route('/admin')
def admin():
    if 'role' not in session: return redirect(url_for('login'))
    config = {c.key: c.value for c in SiteConfig.query.all()}
    return render_template('admin.html', 
                           uploads=UserUpload.query.order_by(UserUpload.id.desc()).all(), 
                           requests=ProjectRequest.query.order_by(ProjectRequest.id.desc()).all(), 
                           products=Product.query.all(),
                           txns=Transaction.query.order_by(Transaction.id.desc()).all(),
                           admins=AdminUser.query.all() if session['role'] == 'superadmin' else [],
                           logs=ActivityLog.query.order_by(ActivityLog.id.desc()).limit(50).all() if session['role'] == 'superadmin' else [],
                           role=session['role'], username=session['username'], config=config)

@app.route('/admin/update-config', methods=['POST'])
def update_config():
    if session.get('role') != 'superadmin': abort(403)
    for key, value in request.form.items():
        conf = SiteConfig.query.filter_by(key=key).first()
        if conf: conf.value = value
    db.session.commit()
    log_action(session['username'], "Updated site configuration text.")
    return redirect(url_for('admin'))

@app.route('/admin/edit-product/<int:id>', methods=['POST'])
def edit_product(id):
    if session.get('role') != 'superadmin': abort(403)
    p = Product.query.get_or_404(id)
    p.description = request.form.get('description')
    p.price = float(request.form.get('price'))
    db.session.commit()
    log_action(session['username'], f"Edited product: {p.name}")
    return redirect(url_for('admin'))

@app.route('/admin/add-product', methods=['POST'])
def add_product():
    if session.get('role') != 'superadmin': abort(403)
    file = request.files.get('file')
    if file and file.filename.endswith('.pdf'):
        fname = secure_filename(file.filename)
        file.save(os.path.join(UPLOAD_DIR, fname))
        prod_name = request.form.get('name')
        db.session.add(Product(name=prod_name, price=float(request.form.get('price')), description=request.form.get('description'), filename=fname))
        db.session.commit()
        log_action(session['username'], f"Published module: {prod_name}")
    return redirect(url_for('admin'))

@app.route('/admin/delete-product/<int:id>', methods=['POST'])
def delete_product(id):
    if session.get('role') != 'superadmin': abort(403)
    p = Product.query.get_or_404(id)
    log_action(session['username'], f"Deleted module: {p.name}")
    db.session.delete(p)
    db.session.commit()
    return jsonify({"success": True})

@app.route('/admin/create-subadmin', methods=['POST'])
def create_subadmin():
    if session.get('role') != 'superadmin': abort(403)
    u = request.form.get('username')
    p = request.form.get('password')
    if not AdminUser.query.filter_by(username=u).first():
        db.session.add(AdminUser(username=u, password=p, role='subadmin'))
        db.session.commit()
        log_action(session['username'], f"Created subadmin: {u}")
    return redirect(url_for('admin'))

@app.route('/admin/toggle-admin/<int:id>', methods=['POST'])
def toggle_admin(id):
    if session.get('role') != 'superadmin': abort(403)
    admin_account = AdminUser.query.get_or_404(id)
    if admin_account.username != 'superadmin':
        admin_account.is_active = not admin_account.is_active
        db.session.commit()
        log_action(session['username'], f"Toggled access for: {admin_account.username}")
    return jsonify({"success": True})

@app.route('/admin/download/<filename>')
def download_file(filename):
    if 'role' not in session: abort(403)
    return send_from_directory(UPLOAD_DIR, filename)

@app.route('/logout')
def logout():
    if 'username' in session: log_action(session['username'], "Logged out")
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)