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
supabase: Client = create_client(os.environ.get("SUPABASE_URL", ""), os.environ.get("SUPABASE_KEY", "")) if os.environ.get("SUPABASE_URL") else None

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
        
        # AUTO-SEED TO FIX EMPTY INVENTORY
        if not Product.query.first():
            db.session.add_all([
                Product(name="AETHER MULTILINGUAL", price=999.0, filename="aether.pdf", description="Verified answers."),
                Product(name="KOBRA CLIPS", price=999.0, filename="kobra.pdf", description="Secure download.")
            ])
        db.session.commit()
    except: pass

# --- PAYMENT GATEWAYS (M-PESA & BINANCE) ---
DARAJA_ENV = os.environ.get('DARAJA_ENV', 'sandbox').lower()
DARAJA_BASE_URL = "https://sandbox.safaricom.co.ke" if DARAJA_ENV == 'sandbox' else "https://api.safaricom.co.ke"

@app.route('/stk-push', methods=['POST'])
def stk_push():
    data = request.json
    prod = Product.query.get(data.get('product_id'))
    key, sec = os.environ.get('DARAJA_CONSUMER_KEY', ''), os.environ.get('DARAJA_CONSUMER_SECRET', '')
    token = requests.get(f"{DARAJA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials", auth=(key, sec)).json().get('access_token')
    
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
        "AccountReference": f"FW_{prod.id}", "TransactionDesc": "Feswide Payment"
    }
    r = requests.post(f"{DARAJA_BASE_URL}/mpesa/stkpush/v1/processrequest", json=payload, headers={"Authorization": f"Bearer {token}"})
    if r.json().get('ResponseCode') == '0':
        db.session.add(Transaction(checkout_request_id=r.json().get('CheckoutRequestID'), phone=phone, amount=prod.price, product_id=prod.id, ip_address=request.remote_addr))
        db.session.commit()
        return jsonify({"status": "success", "checkout_id": r.json().get('CheckoutRequestID')})
    return jsonify({"error": "Failed"}), 400

@app.route('/binance-pay', methods=['POST'])
def binance_pay():
    data = request.json
    prod = Product.query.get(data.get('product_id'))
    api_key, sec_key = os.environ.get('BINANCE_API_KEY', ''), os.environ.get('BINANCE_SECRET_KEY', '')
    trade_no = f"FW_{prod.id}_{int(time.time())}"
    
    payload = {
        "env": {"terminalType": "WEB"}, "merchantTradeNo": trade_no, "orderAmount": round(prod.price / 130.0, 2), "currency": "USDT",
        "goods": {"goodsType": "02", "goodsCategory": "Z000", "referenceGoodsId": str(prod.id), "goodsName": prod.name[:30]}
    }
    ts, nonce = str(int(time.time() * 1000)), ''.join(random.choices(string.ascii_letters, k=32))
    payload_str = json.dumps(payload, separators=(',', ':'))
    msg = f"{ts}\n{nonce}\n{payload_str}\n"
    sig = hmac.new(sec_key.encode('utf-8'), msg.encode('utf-8'), hashlib.sha512).hexdigest().upper()
    
    headers = {"Content-Type":"application/json", "BinancePay-Timestamp":ts, "BinancePay-Nonce":nonce, "BinancePay-Certificate-Sn":api_key, "BinancePay-Signature":sig}
    r = requests.post("https://bpay.binanceapi.com/binancepay/openapi/v2/order", json=payload, headers=headers)
    if r.json().get('status') == 'SUCCESS':
        db.session.add(Transaction(checkout_request_id=trade_no, payment_method='Binance', amount=prod.price, product_id=prod.id, ip_address=request.remote_addr))
        db.session.commit()
        return jsonify({"status": "success", "checkout_url": r.json()['data']['checkoutUrl'], "checkout_id": trade_no})
    return jsonify({"error": "Failed"}), 400

@app.route('/check-payment/<id>')
def check_payment(id):
    t = Transaction.query.filter_by(checkout_request_id=id).first()
    if t and t.status == 'Paid': return jsonify({"status": "Paid", "download_token": t.download_token})
    return jsonify({"status": t.status if t else "Pending"})

@app.route('/')
def index():
    conf = {c.key: c.value for c in SiteConfig.query.all()}
    return render_template('index.html', products=Product.query.all(), config=conf)

@app.route('/admin')
def admin():
    if 'role' not in session: return redirect(url_for('login'))
    return render_template('admin.html', uploads=UserUpload.query.all(), products=Product.query.all(), txns=Transaction.query.order_by(Transaction.id.desc()).all(), admins=AdminUser.query.all(), role=session['role'], username=session['username'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('username'), request.form.get('password')
        admin = AdminUser.query.filter_by(username=u, password=p).first()
        if admin:
            session['role'], session['username'] = admin.role, admin.username
            return redirect(url_for('admin'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)