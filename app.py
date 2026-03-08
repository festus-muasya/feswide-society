from flask import Flask, render_template, request, jsonify, send_from_directory, abort
from models import db, Transaction, UserUpload, User
import os

app = Flask(__name__)

# --- DATABASE CONFIGURATION FOR VERCEL & LOCAL TESTING ---
# Looks for a DATABASE_URL environment variable (used in production on Vercel).
# If it doesn't exist, it falls back to a local SQLite database for your testing.
database_url = os.environ.get('DATABASE_URL', 'sqlite:///feswide.db')

# Vercel/SQLAlchemy requires PostgreSQL URLs to start with 'postgresql://' instead of 'postgres://'
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_secure_fallback_key')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- FILE STORAGE CONFIGURATION ---
# Note: On Vercel, these local folders will reset. You will eventually want to 
# swap this logic out for a cloud storage solution like Amazon S3 or Supabase Storage.
SECURE_ANSWERS_DIR = os.path.abspath('secure_answers')
USER_UPLOADS_DIR = os.path.abspath('user_uploads')

# Ensure directories exist locally
os.makedirs(SECURE_ANSWERS_DIR, exist_ok=True)
os.makedirs(USER_UPLOADS_DIR, exist_ok=True)

# Initialize Database
db.init_app(app)

with app.app_context():
    db.create_all()


# ==========================================
# PUBLIC & STOREFRONT ROUTES
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
    
    # TODO: Insert actual Daraja API STK Push request logic here
    mock_checkout_id = "ws_CO_1234567890" 
    
    # Save pending transaction to the database
    new_txn = Transaction(checkout_request_id=mock_checkout_id, phone=phone, amount=amount, document_name=item)
    db.session.add(new_txn)
    db.session.commit()
    
    return jsonify({"status": "PROMPTED", "checkoutId": mock_checkout_id})

@app.route('/daraja-callback', methods=['POST'])
def daraja_callback():
    # Daraja API hits this route automatically after the user enters their PIN
    callback_data = request.json
    
    # TODO: Parse callback_data to check if payment was successful
    # Example logic: Update Transaction status in DB to 'Paid'
    
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
        
        # Serve the file securely from outside the public folder
        if actual_file:
            return send_from_directory(SECURE_ANSWERS_DIR, actual_file, as_attachment=True)
        else:
            abort(404, description="File not found.")
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
        
        # Save record to DB (In a real app, grab the uploader's phone/ID from their session)
        new_upload = UserUpload(uploader_phone="Current User", filename=file.filename)
        db.session.add(new_upload)
        db.session.commit()
        
        return jsonify({"message": "File securely sent to Superadmin."})


# ==========================================
# ADMIN DASHBOARD ROUTES
# ==========================================

@app.route('/admin')
def admin_dashboard():
    # TODO: In production, add session verification to check if the user is a superadmin/subadmin.
    
    # Fetch all records from the database
    all_uploads = UserUpload.query.order_by(UserUpload.id.desc()).all()
    all_users = User.query.all()
    
    # Pass the database records to the HTML template
    return render_template('admin.html', uploads=all_uploads, users=all_users)

@app.route('/admin/upload/<int:upload_id>/<action>', methods=['POST'])
def manage_upload(upload_id, action):
    # Fetch the specific upload by ID
    upload = UserUpload.query.get_or_404(upload_id)
    
    if action == 'approve':
        upload.status = 'Approved'
        # TODO: Trigger M-Pesa B2C (Business to Customer) API here to pay the user automatically
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