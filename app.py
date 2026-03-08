import os, requests, base64, hmac, hashlib, time, random, string, json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, abort
from models import db, UserUpload, Product, AdminUser, ActivityLog, Transaction, SiteConfig
from werkzeug.utils import secure_filename
from supabase import create_client, Client

app = Flask(__name__)

# --- DATABASE & SECURITY CONFIG ---
database_url = os.environ.get('DATABASE_URL', 'sqlite:////tmp/feswide.db')
if database_url.startswith("postgres://"): 
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fesfast_wide_networks')
db.init_app(app)

# --- SUPABASE FILE STORAGE ---
supabase: Client = create_client(os.environ.get("SUPABASE_URL", ""), os.environ.get("SUPABASE_KEY", "")) if os.environ.get("SUPABASE_URL") else None

# --- AUTO-SEED DATABASE ON BOOT ---
with app.app_context():
    try:
        db.create_all()
        if not AdminUser.query.first():
            db.session.add(AdminUser(username='superadmin', password='FeswideMaster2026!', role='superadmin'))
        
        # This fixes the "Inventory Empty" issue by adding default products
        if not Product.query.first():
            desc = "Verified Feswide Golden Trajectory answers. Secure download restricted to buyer."
            db.session.add_all([
                Product(name="AETHER MULTILINGUAL QUALITY CHECK", price=999.0, filename="aether.pdf", description=desc),
                Product(name="AETHER CODER SCREENING", price=999.0, filename="coder.pdf", description=desc),
                Product(name="KOBRA CLIPS", price=999.0, filename="kobra.pdf", description=desc),
                Product(name="GRAND PRIX", price=999.0, filename="gp.pdf", description=desc)
            ])
        db.session.commit()
    except Exception as e: print(f"Init Error: {e}")

# --- M-PESA DARAJA PRODUCTION LOGIC ---
DARAJA_ENV = os.environ.get('DARAJA_ENV', 'sandbox').lower()
DARAJA_BASE_URL = "https://sandbox.safaricom.co.ke" if DARAJA_ENV == 'sandbox' else "https://api.safaricom.co.ke"

def get_daraja_token():
    key, secret = os.environ.get('DARAJA_CONSUMER_KEY', ''), os.environ.get('DARAJA_CONSUMER_SECRET', '')
    url = f"{DARAJA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials" 
    try:
        r = requests.get(url, auth=(key, secret), timeout=15)
        return r.json().get('access_token'), None if r.status_code == 200 else r.text
    except Exception as e: return None, str(e)

@app.route('/stk-push', methods=['POST'])
def stk_push():
    data = request.json
    product = Product.query.get(data.get('product_id'))
    token, err = get_daraja_token()
    if not token: return jsonify({"error": f"Safaricom Rejected Keys: {err}"}), 500
    
    shortcode = os.environ.get('DARAJA_BUSINESS_SHORTCODE', '174379')
    passkey = os.environ.get('DARAJA_PASSKEY', 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919')
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = base64.b64encode((shortcode + passkey + timestamp).encode()).decode('utf-8')
    phone = data.get('phone')
    if phone.startswith('0'): phone = '254' + phone[1:]

    payload = {
        "BusinessShortCode": shortcode, "Password": password, "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline", "Amount": 1 if DARAJA_ENV == 'sandbox' else int(product.price),
        "PartyA": phone, "PartyB": shortcode, "PhoneNumber": phone,
        "CallBackURL": request.host_url.replace("http", "https") + "daraja-callback",
        "AccountReference": f"FW_{product.id}", "TransactionDesc": "Feswide Module"
    }
    r = requests.post(f"{DARAJA_BASE_URL}/mpesa/stkpush/v1/processrequest", json=payload, headers={"Authorization": f"Bearer {token}"})
    res = r.json()
    if res.get('ResponseCode') == '0':
        db.session.add(Transaction(checkout_request_id=res.get('CheckoutRequestID'), phone=phone, amount=product.price, product_id=product.id, ip_address=request.remote_addr))
        db.session.commit()
        return jsonify({"status": "success", "checkout_id": res.get('CheckoutRequestID')})
    return jsonify({"error": res.get('errorMessage', 'STK Trigger Failed')}), 400

# --- BINANCE PAY USDT CALCULATION ---
@app.route('/binance-pay', methods=['POST'])
def binance_pay():
    data = request.json
    product = Product.query.get(data.get('product_id'))
    api_key, secret_key = os.environ.get('BINANCE_API_KEY', ''), os.environ.get('BINANCE_SECRET_KEY', '')
    
    merchant_trade_no = f"FW_{product.id}_{int(time.time())}"
    # DYNAMIC CALCULATION: KES to USDT (Rate: 130)
    usdt_amount = round(product.price / 130.0, 2)
    
    payload = {
        "env": {"terminalType": "WEB"}, "merchantTradeNo": merchant_trade_no,
        "orderAmount": float(usdt_amount), "currency": "USDT",
        "goods": {"goodsType": "02", "goodsCategory": "Z000", "referenceGoodsId": str(product.id), "goodsName": product.name[:30]}
    }
    
    timestamp = str(int(time.time() * 1000))
    nonce = ''.join(random.choices(string.ascii_letters, k=32))
    payload_str = json.dumps(payload, separators=(',', ':'))
    msg = f"{timestamp}\n{nonce}\n{payload_str}\n"
    signature = hmac.new(secret_key.encode('utf-8'), msg.encode('utf-8'), hashlib.sha512).hexdigest().upper()
    
    headers = {"Content-Type": "application/json", "BinancePay-Timestamp": timestamp, "BinancePay-Nonce": nonce, "BinancePay-Certificate-Sn": api_key, "BinancePay-Signature": signature}
    r = requests.post("https://bpay.binanceapi.com/binancepay/openapi/v2/order", json=payload, headers=headers)
    res = r.json()
    
    if res.get('status') == 'SUCCESS':
        db.session.add(Transaction(checkout_request_id=merchant_trade_no, payment_method='Binance', amount=product.price, product_id=product.id, ip_address=request.remote_addr))
        db.session.commit()
        return jsonify({"status": "success", "checkout_url": res['data']['checkoutUrl'], "checkout_id": merchant_trade_no})
    return jsonify({"error": "Binance Order Failed"}), 400

# --- ADMIN ROUTES ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('username'), request.form.get('password')
        admin = AdminUser.query.filter_by(username=u, password=p).first()
        if admin:
            session['role'], session['username'] = admin.role, admin.username
            return redirect(url_for('admin'))
        return render_template('login.html', error="ACCESS DENIED.")
    return render_template('login.html')

@app.route('/admin')
def admin():
    if 'role' not in session: return redirect(url_for('login'))
    return render_template('admin.html', uploads=UserUpload.query.all(), products=Product.query.all(), txns=Transaction.query.order_by(Transaction.id.desc()).all(), role=session['role'], username=session['username'])

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

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)