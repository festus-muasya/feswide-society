import os
from flask import Flask, render_template, request, jsonify, send_from_directory, abort
from models import db, Transaction, UserUpload, User

app = Flask(__name__)

# ==========================================
# 1. DATABASE CONFIGURATION 
# ==========================================
# Pulls your encoded Supabase string from Vercel. 
# Falls back to local SQLite if you test on your own computer.
database_url = os.environ.get('DATABASE_URL', 'sqlite:///feswide.db')

# SQLAlchemy requires 'postgresql://' instead of 'postgres://'
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ==========================================
# 2. SECURITY & API CREDENTIALS
# ==========================================
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback_secret_key_for_local_testing')

# Daraja Credentials (Ready for when you set them in Vercel)
DARAJA_CONSUMER_KEY = os.environ.get('DARAJA_CONSUMER_KEY', '')
DARAJA_CONSUMER_SECRET = os.environ.get('DARAJA_CONSUMER_SECRET', '')
DARAJA_PASSKEY = os.environ.get('DARAJA_PASSKEY', '')
DARAJA_BUSINESS_SHORTCODE = os.environ.get('DARAJA_BUSINESS_SHORTCODE', '')

# ==========================================
# 3. FILE STORAGE (VERCEL READ-ONLY FIX)
# ==========================================
# Secure answers are part of your GitHub repo, so they live in the main folder
SECURE_ANSWERS_DIR = os.path.join(os.path.dirname(__file__), 'secure_answers')

# User uploads MUST go to the temporary /tmp folder when running on Vercel
if os.environ.get('VERCEL_ENV') or os.environ.get('VERCEL_URL'):
    USER_UPLOADS_DIR = '/tmp/user_uploads'
else:
    USER_UPLOADS_DIR = os.path.join(os.path.dirname(__file__), 'user_uploads')

# Create the upload directory if it doesn't exist
os.makedirs(USER_UPLOADS_DIR, exist_ok=True)


# ==========================================
# 4. INITIALIZE DATABASE
# ==========================================
db.init_app(app)

with app.app_context():
    # Creates tables in Supabase if they don't exist yet
    db.create_all()


# ==========================================
# 5. PUBLIC & STOREFRONT ROUTES
# ==========================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/pay-stk', methods=['POST'])
def pay_stk():
    data = request.json
    phone = data.get('phone')
    item = data.get('item')
    amount = data.get('amount')
    
    # Placeholder for actual Daraja STK Push logic
    mock_checkout_id = "ws_CO_1234567890" 
    
    # Save pending transaction to the database
    new_txn = Transaction(
        checkout_request_id=mock_checkout_id, 
        phone=phone, 
        amount=amount, 
        document_name=item
    )
    db.session.add(new_txn)
    db.session.commit()
    
    return jsonify({"status": "PROMPTED", "checkoutId": mock_checkout_id})

@app.route('/daraja-callback', methods=['POST'])
def daraja_callback():
    # Daraja API hits this route automatically after the user enters their PIN
    callback_data = request.json
    
    # Placeholder for checking if payment was successful and updating the DB
    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})

@app.route('/download/<checkout_id>')
def download_document(checkout_id):
    # Only allow download if the database says this checkout_id is 'Paid'
    txn = Transaction.query.filter_by(checkout_request_id=checkout_id).first()
    
    if txn and txn.status == 'Paid':
        # Map item name to actual filename
        filename_map = {
            "Aether Multilingual Quality Check": "aether_module.pdf",
            "Aether Coder Screening Module": "coder_module.pdf",
            "Pre-Test Quality Screening": "pretest_module.pdf"
        }
        actual_file = filename_map.get(txn.document_name)
        
        # Serve the file securely
        if actual_file:
            return send_from_directory(SECURE_ANSWERS_DIR, actual_file, as_attachment=True)
        else:
            abort(404, description="File not found in system.")
    else:
        abort(403, description="Payment not completed or unauthorized.")

@app.route('/upload-answer', methods=['POST'])
def upload_answer():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
        
    file = request.files['file']
    if file.filename != '':
        filepath = os.path.join(USER_UPLOADS_DIR, file.filename)
        file.save(filepath)
        
        # Save upload record to DB
        new_upload = UserUpload(uploader_phone="Current User", filename=file.filename)
        db.session.add(new_upload)
        db.session.commit()
        
        return jsonify({"message": "File securely sent to Superadmin."})


# ==========================================
# 6. ADMIN DASHBOARD ROUTES
# ==========================================

@app.route('/admin')
def admin_dashboard():
    # Fetch all records from the database to display in the HTML tables
    all_uploads = UserUpload.query.order_by(UserUpload.id.desc()).all()
    all_users = User.query.all()
    
    return render_template('admin.html', uploads=all_uploads, users=all_users)

@app.route('/admin/upload/<int:upload_id>/<action>', methods=['POST'])
def manage_upload(upload_id, action):
    # Fetch the specific upload by ID
    upload = UserUpload.query.get_or_404(upload_id)
    
    if action == 'approve':
        upload.status = 'Approved'
        # Placeholder for triggering M-Pesa B2C payout
    elif action == 'reject':
        upload.status = 'Rejected'
    else:
        return jsonify({"success": False, "message": "Invalid action."}), 400
        
    db.session.commit()
    return jsonify({"success": True, "message": f"Document {action}d successfully."})

@app.route('/admin/user/<int:user_id>/<role>', methods=['POST'])
def manage_user(user_id, role):
    # Fetch the specific user by ID
    user = User.query.get_or_404(user_id)
    
    valid_roles = ['user', 'subadmin', 'superadmin', 'suspended']
    if role in valid_roles:
        user.role = role
        db.session.commit()
        return jsonify({"success": True, "message": f"User role updated to {role}."})
        
    return jsonify({"success": False, "message": "Invalid role."}), 400


if __name__ == '__main__':
    app.run(debug=True)