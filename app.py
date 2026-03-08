import os, requests, base64, hmac, hashlib, time, random, string, json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, abort
from models import db, UserUpload, Product, AdminUser, ActivityLog, Transaction, SiteConfig, Opportunity
from werkzeug.utils import secure_filename
from supabase import create_client, Client

app = Flask(__name__)

# --- DATABASE CONFIG ---
database_url = os.environ.get('DATABASE_URL', 'sqlite:////tmp/feswide_v4.db')
if database_url.startswith("postgres://"): 
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'feswide_enc_2026_prod')
db.init_app(app)

# --- STORAGE CONFIG ---
sb_url = os.environ.get("SUPABASE_URL", "")
sb_key = os.environ.get("SUPABASE_KEY", "")
supabase: Client = create_client(sb_url, sb_key) if sb_url and sb_key else None

def log_action(op, act):
    try:
        db.session.add(ActivityLog(operator=op, action=act))
        db.session.commit()
    except: pass

# --- AUTO-BOOT SEQUENCE ---
with app.app_context():
    try:
        db.create_all()
        # Initialize Master Superadmin
        if not AdminUser.query.filter_by(username='superadmin').first():
            db.session.add(AdminUser(username='superadmin', password='FeswideMaster2026!', role='superadmin'))
        
        # Initialize Global Config
        if not SiteConfig.query.filter_by(key='hero_text').first():
            db.session.add(SiteConfig(key='hero_text', value="Feswide Society Index. Secure OPSEC Modules."))
        
        # Restore Official Verified Inventory
        if not Product.query.first():
            db.session.add_all([
                Product(name="AETHER MULTILINGUAL QUALITY CHECK", price=999.0, filename="aether.pdf", description="Tested and they are 100% accurate"),
                Product(name="AETHER CODER SCREENING", price=999.0, filename="coder.pdf", description="Tested and they are 100% accurate"),
                Product(name="KOBRA CLIPS", price=999.0, filename="kobra.pdf", description="Tested and they are 100% accurate"),
                Product(name="GRAND PRIX", price=999.0, filename="gp.pdf", description="Tested and they are 100% accurate")
            ])
        db.session.commit()
    except Exception as e: print(f"BOOT_ERROR: {e}")

# ==========================================
# 1. GATEWAY: LIPA NA M-PESA (STK PUSH)
# ==========================================
DARAJA_ENV = os.environ.get('DARAJA_ENV', 'sandbox').lower()
DARAJA_BASE_URL = "https://sandbox.safaricom.co.ke" if DARAJA_ENV == 'sandbox' else "https://api.safaricom.co.ke"

def get_daraja_token():
    key = os.environ.get('DARAJA_CONSUMER_KEY', '').strip()
    sec = os.environ.get('DARAJA_CONSUMER_SECRET', '').strip()
    try:
        r = requests.get(f"{DARAJA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials", auth=(key, sec), timeout=15)
        return r.json().get('access_token')
    except: return None

@app.route('/stk-push', methods=['POST'])
def stk_push():
    data = request.json
    prod = Product.query.get(data.get('product_id'))
    token = get_daraja_token()
    if not token: return jsonify({"error": "Gateway Auth Failed"}), 500
    
    shortcode = os.environ.get('DARAJA_BUSINESS_SHORTCODE', '174379').strip()
    passkey = os.environ.get('DARAJA_PASSKEY', 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919').strip()
    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    pw = base64.b64encode((shortcode + passkey + ts).encode()).decode('utf-8')
    phone = data.get('phone').replace('+', '')
    if phone.startswith('0'): phone = '254' + phone[1:]

    payload = {
        "BusinessShortCode": shortcode, "Password": pw, "Timestamp": ts,
        "TransactionType": "CustomerPayBillOnline", "Amount": 1 if DARAJA_ENV == 'sandbox' else int(prod.price),
        "PartyA": phone, "PartyB": shortcode, "PhoneNumber": phone,
        "CallBackURL": request.host_url.replace("http", "https") + "daraja-callback",
        "AccountReference": f"FW_{prod.id}", "TransactionDesc": "Feswide Society"
    }
    r = requests.post(f"{DARAJA_BASE_URL}/mpesa/stkpush/v1/processrequest", json=payload, headers={"Authorization": f"Bearer {token}"})
    if r.json().get('ResponseCode') == '0':
        db.session.add(Transaction(checkout_request_id=r.json().get('CheckoutRequestID'), phone=phone, amount=prod.price, product_id=prod.id, ip_address=request.remote_addr))
        db.session.commit()
        return jsonify({"status": "success", "checkout_id": r.json().get('CheckoutRequestID')})
    return jsonify({"error": "STK Prompt Failed"}), 400

# ==========================================
# 2. GATEWAY: BINANCE PAY (USDT BEP-20)
# ==========================================
@app.route('/binance-pay', methods=['POST'])
def binance_pay():
    data = request.json
    prod = Product.query.get(data.get('product_id'))
    api_key = os.environ.get('BINANCE_API_KEY', '').strip()
    sec_key = os.environ.get('BINANCE_SECRET_KEY', '').strip()
    trade_no = f"FW_{prod.id}_{int(time.time())}"
    
    # KES to USDT conversion (Fixed rate 130)
    usdt = round(prod.price / 130.0, 2)
    
    payload = {
        "env": {"terminalType": "WEB"}, "merchantTradeNo": trade_no, "orderAmount": usdt, "currency": "USDT",
        "goods": {"goodsType": "02", "goodsCategory": "Z000", "referenceGoodsId": str(prod.id), "goodsName": prod.name[:30]}
    }
    ts, nonce = str(int(time.time() * 1000)), ''.join(random.choices(string.ascii_letters, k=32))
    payload_str = json.dumps(payload, separators=(',', ':'))
    msg = f"{ts}\n{nonce}\n{payload_str}\n"
    sig = hmac.new(sec_key.encode('utf-8'), msg.encode('utf-8'), hashlib.sha512).hexdigest().upper()
    
    headers = {"Content-Type":"application/json", "BinancePay-Timestamp":ts, "BinancePay-Nonce":nonce, "BinancePay-Certificate-Sn":api_key, "BinancePay-Signature":sig}
    r = requests.post("https://bpay.binanceapi.com/binancepay/openapi/v2/order", json=payload, headers=headers)
    res = r.json()
    if res.get('status') == 'SUCCESS':
        db.session.add(Transaction(checkout_request_id=trade_no, payment_method='Binance', amount=prod.price, product_id=prod.id, ip_address=request.remote_addr))
        db.session.commit()
        return jsonify({"status": "success", "checkout_url": res['data']['checkoutUrl'], "checkout_id": trade_no})
    return jsonify({"error": "Binance Order Failed"}), 400

# ==========================================
# 3. OPPORTUNITIES & MARKETPLACE
# ==========================================
@app.route('/post-opportunity', methods=['POST'])
def post_opp():
    new_opp = Opportunity(
        type=request.form.get('type'),
        platform=request.form.get('platform'),
        rate=request.form.get('rate'),
        whatsapp=request.form.get('whatsapp')
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
        db.session.add(UserUpload(
            platform=request.form.get('platform'),
            project_name=request.form.get('project'),
            mpesa_number=request.form.get('payment_id'),
            filename=fn
        ))
        db.session.commit()
    return jsonify({"message": "Submission Logged. Verification in progress (48hrs max)."})

# ==========================================
# 4. SITE CONTENT & PUBLIC ROUTES
# ==========================================
@app.route('/')
def index():
    conf = {c.key: c.value for c in SiteConfig.query.all()}
    hiring = Opportunity.query.filter_by(type='Hiring').all()
    taskers = Opportunity.query.filter_by(type='Tasker').all()
    return render_template('index.html', products=Product.query.all(), config=conf, hiring=hiring, taskers=taskers)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('username'), request.form.get('password')
        admin = AdminUser.query.filter_by(username=u, password=p).first()
        if admin:
            session['role'], session['username'] = admin.role, admin.username
            return redirect(url_for('admin'))
        return render_template('login.html', error="INVALID ACCESS CREDENTIALS")
    return render_template('login.html')

# ==========================================
# 5. SUPERADMIN COMMAND CENTER
# ==========================================
@app.route('/admin')
def admin():
    if 'role' not in session: return redirect(url_for('login'))
    conf_text = SiteConfig.query.filter_by(key='hero_text').first().value
    return render_template('admin.html', 
                           txns=Transaction.query.order_by(Transaction.id.desc()).all(),
                           products=Product.query.all(),
                           uploads=UserUpload.query.all(),
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

@app.route('/admin/add-product', methods=['POST'])
def add_product():
    if session.get('role') != 'superadmin': abort(403)
    f = request.files.get('file')
    if f:
        fn = secure_filename(f.filename)
        if supabase: supabase.storage.from_("feswide-pdfs").upload(fn, f.read())
        db.session.add(Product(name=request.form.get('name'), price=float(request.form.get('price')), description=request.form.get('description'), filename=fn))
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