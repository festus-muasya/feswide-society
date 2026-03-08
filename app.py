import os, requests, base64, hmac, hashlib, time, random, string, json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, abort
from models import db, UserUpload, Product, AdminUser, ActivityLog, Transaction, SiteConfig
from werkzeug.utils import secure_filename
from supabase import create_client, Client

app = Flask(__name__)

# --- DATABASE CONFIG ---
database_url = os.environ.get('DATABASE_URL', 'sqlite:////tmp/feswide.db')
if database_url.startswith("postgres://"): 
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'feswide_enc_2026')
db.init_app(app)

# --- STORAGE ---
sb_url = os.environ.get("SUPABASE_URL", "")
sb_key = os.environ.get("SUPABASE_KEY", "")
supabase: Client = create_client(sb_url, sb_key) if sb_url and sb_key else None

def log_action(op, act):
    try:
        db.session.add(ActivityLog(operator=op, action=act))
        db.session.commit()
    except: pass

with app.app_context():
    try:
        db.create_all()
        if not AdminUser.query.filter_by(username='superadmin').first():
            db.session.add(AdminUser(username='superadmin', password='FeswideMaster2026!', role='superadmin'))
        if not SiteConfig.query.filter_by(key='hero_text').first():
            db.session.add(SiteConfig(key='hero_text', value="Feswide Society Index. Secure OPSEC Modules."))
        db.session.commit()
    except: pass

# --- M-PESA GATEWAY ---
DARAJA_ENV = os.environ.get('DARAJA_ENV', 'sandbox').lower()
DARAJA_BASE_URL = "https://sandbox.safaricom.co.ke" if DARAJA_ENV == 'sandbox' else "https://api.safaricom.co.ke"

def get_daraja_token():
    key, sec = os.environ.get('DARAJA_CONSUMER_KEY', ''), os.environ.get('DARAJA_CONSUMER_SECRET', '')
    url = f"{DARAJA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials" 
    try:
        r = requests.get(url, auth=(key, sec), timeout=15)
        return r.json().get('access_token')
    except: return None

@app.route('/stk-push', methods=['POST'])
def stk_push():
    data = request.json
    prod = Product.query.get(data.get('product_id'))
    token = get_daraja_token()
    if not token: return jsonify({"error": "Auth Failed"}), 500
    
    shortcode = os.environ.get('DARAJA_BUSINESS_SHORTCODE', '174379')
    passkey = os.environ.get('DARAJA_PASSKEY', 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919')
    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    pw = base64.b64encode((shortcode + passkey + ts).encode()).decode('utf-8')
    phone = data.get('phone').replace('+', '')
    if phone.startswith('0'): phone = '254' + phone[1:]

    payload = {
        "BusinessShortCode": shortcode, "Password": pw, "Timestamp": ts,
        "TransactionType": "CustomerPayBillOnline", "Amount": 1 if DARAJA_ENV == 'sandbox' else int(prod.price),
        "PartyA": phone, "PartyB": shortcode, "PhoneNumber": phone,
        "CallBackURL": request.host_url.replace("http://", "https://") + "daraja-callback",
        "AccountReference": f"FW_{prod.id}", "TransactionDesc": "Feswide Module"
    }
    r = requests.post(f"{DARAJA_BASE_URL}/mpesa/stkpush/v1/processrequest", json=payload, headers={"Authorization": f"Bearer {token}"})
    res = r.json()
    if res.get('ResponseCode') == '0':
        db.session.add(Transaction(checkout_request_id=res.get('CheckoutRequestID'), phone=phone, amount=prod.price, product_id=prod.id, ip_address=request.remote_addr))
        db.session.commit()
        return jsonify({"status": "success", "checkout_id": res.get('CheckoutRequestID')})
    return jsonify({"error": "Failed"}), 400

# --- BINANCE GATEWAY ---
@app.route('/binance-pay', methods=['POST'])
def binance_pay():
    data = request.json
    prod = Product.query.get(data.get('product_id'))
    api_key, sec_key = os.environ.get('BINANCE_API_KEY', ''), os.environ.get('BINANCE_SECRET_KEY', '')
    trade_no = f"FW_{prod.id}_{int(time.time())}"
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
    return jsonify({"error": "Binance Failed"}), 400

# --- UTILITY ---
@app.route('/check-payment/<id>')
def check_payment(id):
    t = Transaction.query.filter_by(checkout_request_id=id).first()
    if t and t.status == 'Paid': return jsonify({"status": "Paid", "download_token": t.download_token})
    return jsonify({"status": t.status if t else "Pending"})

@app.route('/')
def index():
    conf = {c.key: c.value for c in SiteConfig.query.all()}
    return render_template('index.html', products=Product.query.all(), config=conf)

@app.route('/api/chat', methods=['POST'])
def chat():
    return jsonify({"reply": "I am Agent Faith. How can I help you with your purchase?"})

# --- ADMIN ROUTES ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('username'), request.form.get('password')
        admin = AdminUser.query.filter_by(username=u, password=p).first()
        if admin:
            session['role'], session['username'] = admin.role, admin.username
            return redirect(url_for('admin'))
    return render_template('login.html')

@app.route('/admin')
def admin():
    if 'role' not in session: return redirect(url_for('login'))
    return render_template('admin.html', uploads=UserUpload.query.all(), products=Product.query.all(), txns=Transaction.query.order_by(Transaction.id.desc()).all(), admins=AdminUser.query.all(), role=session['role'], username=session['username'])

@app.route('/admin/delete-product/<int:id>', methods=['POST'])
def delete_product(id):
    if session.get('role') != 'superadmin': abort(403)
    p = Product.query.get(id)
    if p:
        db.session.delete(p)
        db.session.commit()
        log_action(session['username'], f"Deleted product: {p.name}")
    return redirect(url_for('admin'))

@app.route('/admin/add-product', methods=['POST'])
def add_product():
    if session.get('role') != 'superadmin': abort(403)
    f = request.files.get('file')
    if f and f.filename.endswith('.pdf'):
        fn = secure_filename(f.filename)
        if supabase: supabase.storage.from_("feswide-pdfs").upload(fn, f.read())
        db.session.add(Product(name=request.form.get('name'), price=float(request.form.get('price')), description=request.form.get('description'), filename=fn))
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