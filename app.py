import os, requests, base64, hmac, hashlib, time, random, string, json
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

# --- SUPABASE FILE STORAGE ---
sb_url = os.environ.get("SUPABASE_URL", "")
sb_key = os.environ.get("SUPABASE_KEY", "")
supabase: Client = create_client(sb_url, sb_key) if sb_url and sb_key else None

def log_action(operator, action):
    try:
        db.session.add(ActivityLog(operator=operator, action=action))
        db.session.commit()
    except Exception: pass

with app.app_context():
    try:
        db.create_all()
        if not AdminUser.query.first():
            db.session.add(AdminUser(username='superadmin', password='FeswideMaster2026!', role='superadmin'))
        if not SiteConfig.query.filter_by(key='hero_text').first():
            db.session.add(SiteConfig(key='hero_text', value="Feswide Society Index. Secure OPSEC Modules."))
            db.session.add(SiteConfig(key='upload_notice', value="Requirement: Submit your completed PDF for review."))
        db.session.commit()
    except Exception as e: print(f"Boot Error: {e}")

# ==========================================
# GATEWAY 1: LIPA NA M-PESA (STK PUSH)
# ==========================================
DARAJA_ENV = os.environ.get('DARAJA_ENV', 'sandbox').lower()
DARAJA_BASE_URL = "https://sandbox.safaricom.co.ke" if DARAJA_ENV == 'sandbox' else "https://api.safaricom.co.ke"

def get_daraja_token():
    key = os.environ.get('DARAJA_CONSUMER_KEY', '').strip()
    secret = os.environ.get('DARAJA_CONSUMER_SECRET', '').strip()
    url = f"{DARAJA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials" 
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
        if not token: return jsonify({"error": f"Safaricom Auth Rejected. Check Vercel Keys."}), 500

        shortcode = os.environ.get('DARAJA_BUSINESS_SHORTCODE', '174379').strip()
        passkey = os.environ.get('DARAJA_PASSKEY', 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919').strip()
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password = base64.b64encode((shortcode + passkey + timestamp).encode()).decode('utf-8')

        if phone.startswith('0'): phone = '254' + phone[1:]
        elif phone.startswith('+'): phone = phone[1:]
        
        cb_url = request.host_url.rstrip('/') + "/daraja-callback"
        cb_url = cb_url.replace("http://", "https://") if "localhost" not in cb_url else cb_url

        payload = {
            "BusinessShortCode": shortcode, "Password": password, "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline", "Amount": int(product.price) if DARAJA_ENV == 'production' else 1, 
            "PartyA": phone, "PartyB": shortcode, "PhoneNumber": phone,
            "CallBackURL": cb_url, "AccountReference": f"FW_{product.id}", "TransactionDesc": "Feswide Module"
        }

        r = requests.post(f"{DARAJA_BASE_URL}/mpesa/stkpush/v1/processrequest", json=payload, headers={"Authorization": f"Bearer {token}"}, timeout=20)
        res = r.json()
        
        if res.get('ResponseCode') == '0':
            db.session.add(Transaction(checkout_request_id=res.get('CheckoutRequestID'), phone=phone, amount=product.price, product_id=product.id, ip_address=request.remote_addr))
            db.session.commit()
            return jsonify({"status": "success", "checkout_id": res.get('CheckoutRequestID')})
            
        return jsonify({"error": res.get('errorMessage', 'STK Push Failed.')}), 400
    except Exception as e: return jsonify({"error": str(e)}), 500

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

# ==========================================
# GATEWAY 2: BINANCE PAY (USDT - BEP20)
# ==========================================
@app.route('/binance-pay', methods=['POST'])
def binance_pay():
    try:
        data = request.json
        product = Product.query.get(data.get('product_id'))
        
        api_key = os.environ.get('BINANCE_API_KEY', '').strip()
        secret_key = os.environ.get('BINANCE_SECRET_KEY', '').strip()
        
        if not api_key or not secret_key:
            return jsonify({"error": "Binance Merchant API Keys missing in Vercel."}), 500
            
        merchant_trade_no = f"FW_{product.id}_{int(time.time())}"
        
        # EXACT CONVERSION CALCULATION: KES to USDT
        # You can adjust this exchange rate variable as needed.
        EXCHANGE_RATE = 130.0 
        usdt_amount = round(product.price / EXCHANGE_RATE, 2)
        if usdt_amount < 0.1: usdt_amount = 0.1 # Binance Pay minimum transaction limit
        
        payload = {
            "env": { "terminalType": "WEB" },
            "merchantTradeNo": merchant_trade_no,
            "orderAmount": float(usdt_amount),
            "currency": "USDT",
            "goods": {
                "goodsType": "02", "goodsCategory": "Z000",
                "referenceGoodsId": str(product.id),
                "goodsName": product.name[:30], "goodsDetail": "Feswide Society Module"
            },
            "returnUrl": request.host_url.rstrip('/') + f"/check-payment/{merchant_trade_no}"
        }
        
        # BINANCE HMAC SHA512 SECURITY SIGNATURE
        timestamp = str(int(time.time() * 1000))
        nonce = ''.join(random.choices(string.ascii_letters, k=32))
        payload_str = json.dumps(payload, separators=(',', ':'))
        msg = f"{timestamp}\n{nonce}\n{payload_str}\n"
        signature = hmac.new(secret_key.encode('utf-8'), msg.encode('utf-8'), hashlib.sha512).hexdigest().upper()
        
        headers = {
            "Content-Type": "application/json",
            "BinancePay-Timestamp": timestamp,
            "BinancePay-Nonce": nonce,
            "BinancePay-Certificate-Sn": api_key,
            "BinancePay-Signature": signature
        }
        
        r = requests.post("https://bpay.binanceapi.com/binancepay/openapi/v2/order", json=payload, headers=headers, timeout=15)
        res = r.json()
        
        if res.get('status') == 'SUCCESS':
            db.session.add(Transaction(checkout_request_id=merchant_trade_no, phone="BINANCE USDT", amount=product.price, product_id=product.id, status='Pending', ip_address=request.remote_addr))
            db.session.commit()
            return jsonify({"status": "success", "checkout_url": res['data']['checkoutUrl'], "checkout_id": merchant_trade_no})
        return jsonify({"error": res.get('errorMessage', 'Binance Order Generation Failed')}), 400
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/binance-callback', methods=['POST'])
def binance_callback():
    try:
        data = request.json
        if data and data.get('bizStatus') == 'PAY_SUCCESS':
            txn = Transaction.query.filter_by(checkout_request_id=data.get('merchantTradeNo')).first()
            if txn:
                txn.status = 'Paid'
                db.session.commit()
        return jsonify({"returnCode": "SUCCESS", "returnMessage": None})
    except Exception: return jsonify({"returnCode": "FAIL", "returnMessage": "Error"}), 500

# ==========================================
# UNIVERSAL ROUTES
# ==========================================
@app.route('/check-payment/<checkout_id>')
def check_payment(checkout_id):
    try:
        txn = Transaction.query.filter_by(checkout_request_id=checkout_id).first()
        if txn and txn.status == 'Paid': return jsonify({"status": "Paid", "download_token": txn.download_token})
        return jsonify({"status": txn.status if txn else "Pending"})
    except Exception: return jsonify({"status": "Error"})

@app.route('/secure-download/<token>')
def secure_download(token):
    try:
        txn = Transaction.query.filter_by(download_token=token).first()
        if not txn or txn.status != 'Paid': abort(403)
        if txn.ip_address and txn.ip_address != request.remote_addr: return "SECURITY BREACH DETECTED: IP Address mismatch.", 403
        if txn.download_count >= 3: return "ACCESS DENIED: Limit reached.", 403
        
        product = Product.query.get(txn.product_id)
        txn.download_count += 1
        db.session.commit()
        if supabase:
            res = supabase.storage.from_('feswide-pdfs').create_signed_url(product.filename, 60)
            return redirect(res['signedURL'])
        return "Supabase File Bucket not linked.", 500
    except Exception as e: return f"Download Error: {e}", 500

@app.route('/')
def index():
    try:
        config = {c.key: c.value for c in SiteConfig.query.all()}
        products = Product.query.all()
    except Exception:
        config = {'hero_text': 'DATABASE OFFLINE. CHECK LOGS.', 'upload_notice': ''}
        products = []
    return render_template('index.html', products=products, config=config)

@app.route('/upload-answer', methods=['POST'])
def upload_answer():
    file = request.files.get('file')
    if file and file.filename.endswith('.pdf'):
        fname = secure_filename(file.filename)
        if supabase:
            supabase.storage.from_("feswide-pdfs").upload(fname, file.read())
            db.session.add(UserUpload(platform=request.form.get('platform'), project_name=request.form.get('project_name'), mpesa_number=request.form.get('mpesa_number'), filename=fname))
            db.session.commit()
            return jsonify({"status": "success", "message": "Uploaded securely."})
        return jsonify({"status": "error", "message": "Supabase not configured."}), 500
    return jsonify({"status": "error", "message": "Invalid file. PDFs only."}), 400

@app.route('/api/chat', methods=['POST'])
def faith_chat():
    return jsonify({"reply": "I am Agent Faith. Contact support@feswide.com for secure handling."})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('username'), request.form.get('password')
        admin_user = AdminUser.query.filter_by(username=u, password=p).first()
        if admin_user and admin_user.is_active:
            session['role'], session['username'] = admin_user.role, admin_user.username
            return redirect(url_for('admin'))
        return render_template('login.html', error="ACCESS DENIED.")
    return render_template('login.html')

@app.route('/admin')
def admin():
    if 'role' not in session: return redirect(url_for('login'))
    config = {c.key: c.value for c in SiteConfig.query.all()}
    return render_template('admin.html', uploads=UserUpload.query.order_by(UserUpload.id.desc()).all(), products=Product.query.all(), txns=Transaction.query.order_by(Transaction.id.desc()).all(), admins=AdminUser.query.all() if session['role'] == 'superadmin' else [], role=session['role'], username=session['username'], config=config)

@app.route('/admin/add-product', methods=['POST'])
def add_product():
    if session.get('role') != 'superadmin': abort(403)
    file = request.files.get('file')
    if file and file.filename.endswith('.pdf'):
        fname = secure_filename(file.filename)
        if supabase: supabase.storage.from_("feswide-pdfs").upload(fname, file.read())
        db.session.add(Product(name=request.form.get('name'), price=float(request.form.get('price')), description=request.form.get('description'), filename=fname))
        db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/update-config', methods=['POST'])
def update_config():
    if session.get('role') != 'superadmin': abort(403)
    for key, value in request.form.items():
        conf = SiteConfig.query.filter_by(key=key).first()
        if conf: conf.value = value
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/create-subadmin', methods=['POST'])
def create_subadmin():
    if session.get('role') != 'superadmin': abort(403)
    u, p = request.form.get('username'), request.form.get('password')
    if not AdminUser.query.filter_by(username=u).first():
        db.session.add(AdminUser(username=u, password=p, role='subadmin'))
        db.session.commit()
    return redirect(url_for('admin'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)