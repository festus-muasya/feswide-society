import os
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, session, abort
from models import db, UserUpload, Product, ProjectRequest, User
from werkzeug.utils import secure_filename

app = Flask(__name__, instance_path='/tmp/instance')

# --- CONFIGURATION & DATABASE ---
database_url = os.environ.get('DATABASE_URL', 'sqlite:////tmp/feswide.db')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'feswide_high_security_2026')

# Vercel Read-Only File System Fix
UPLOAD_DIR = '/tmp/uploads' if os.environ.get('VERCEL_ENV') else os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

db.init_app(app)

with app.app_context():
    db.create_all()
    # Seed default products if empty
    if not Product.query.first():
        db.session.add_all([
            Product(name="Aether Coder Screening", price=999.0, filename="coder.pdf", description="Verified coding trajectories and rubrics."),
            Product(name="Grand Prix English Evaluation", price=999.0, filename="gp.pdf", description="Comprehensive assessment guidelines and answers."),
            Product(name="Kobra Clips Multimodal", price=999.0, filename="kobra.pdf", description="Video and image labeling operational protocols.")
        ])
        db.session.commit()

# --- AGENT FAITH (HUMAN-LIKE AI) ---
@app.route('/api/chat', methods=['POST'])
def faith_chat():
    msg = request.json.get('message', '').lower()
    
    if any(word in msg for word in ["hi", "hello", "hey", "greetings"]):
        reply = "Hello there. I am Agent Faith, the automated assistant for Feswide Society. How can I assist you with our repository or contributor portal today?"
    elif any(word in msg for word in ["price", "cost", "pay", "money", "how much"]):
        reply = "Our premium crack modules are priced at KES 999. If you are a contributor looking to upload answers, we pay KES 500 per verified PDF project submission after a 48-hour manual review."
    elif any(word in msg for word in ["upload", "submit", "contribute"]):
        reply = "You can securely upload your Handshake or Outlier PDFs using the Contributor Hub on this page. Please ensure you provide a valid M-Pesa number so our admins can process your KES 500 payment upon approval."
    elif any(word in msg for word in ["crack", "missing", "vote", "request"]):
        reply = "If you cannot find the specific project you need, please log the exact project name in the Vote Box. Our engineering team monitors these requests and prioritizes cracking high-demand projects within 48 hours."
    elif any(word in msg for word in ["human", "person", "admin", "support", "contact"]):
        reply = "I am an AI agent designed to handle initial inquiries. If you require manual administrative override or human support, please contact our team directly at support@feswide.com."
    else:
        reply = "I am analyzing your request. Our database focuses strictly on Outlier and Handshake AI data. Could you please specify if you are looking to purchase a module, upload a contribution, or request a new crack?"
    
    return jsonify({"reply": reply})

# --- USER ROUTES ---
@app.route('/')
def index():
    return render_template('index.html', products=Product.query.all())

@app.route('/upload-answer', methods=['POST'])
def upload_answer():
    file = request.files.get('file')
    if file and file.filename.endswith('.pdf'):
        fname = secure_filename(file.filename)
        file.save(os.path.join(UPLOAD_DIR, fname))
        db.session.add(UserUpload(
            platform=request.form.get('platform'), 
            project_name=request.form.get('project_name'), 
            mpesa_number=request.form.get('mpesa_number'), 
            filename=fname
        ))
        db.session.commit()
        return jsonify({"message": "UPLOAD SUCCESSFUL. MANUAL REVIEW INITIATED. PAYOUT PENDING (48HRS)."})
    return jsonify({"error": "UPLOAD FAILED. ONLY PDF FORMAT IS ACCEPTED."}), 400

@app.route('/request-project', methods=['POST'])
def request_project():
    data = request.json
    db.session.add(ProjectRequest(project_name=data.get('project_name'), platform=data.get('platform')))
    db.session.commit()
    return jsonify({"success": True})

# --- ADMIN PERMISSIONS & DASHBOARD ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')
        
        # Superadmin Credentials
        if u == 'superadmin' and p == 'FeswideMaster2026!':
            session['role'] = 'superadmin'
            return redirect(url_for('admin'))
        # Subadmin Credentials
        elif u == 'subadmin' and p == 'FeswideStaff!':
            session['role'] = 'subadmin'
            return redirect(url_for('admin'))
            
        return "ACCESS DENIED. INVALID CREDENTIALS.", 401
    return render_template('login.html')

@app.route('/admin')
def admin():
    if 'role' not in session:
        return redirect(url_for('login'))
    return render_template('admin.html', 
                           uploads=UserUpload.query.order_by(UserUpload.id.desc()).all(), 
                           requests=ProjectRequest.query.order_by(ProjectRequest.id.desc()).all(), 
                           products=Product.query.all(),
                           role=session['role'])

@app.route('/admin/add-product', methods=['POST'])
def add_product():
    if session.get('role') != 'superadmin':
        abort(403) # Only Superadmin can add products
        
    file = request.files.get('file')
    if file and file.filename.endswith('.pdf'):
        fname = secure_filename(file.filename)
        file.save(os.path.join(UPLOAD_DIR, fname))
        db.session.add(Product(
            name=request.form.get('name'), 
            price=float(request.form.get('price')), 
            description=request.form.get('description'),
            filename=fname
        ))
        db.session.commit()
        return redirect(url_for('admin'))
    return "Failed to upload. Must be a PDF.", 400

@app.route('/admin/delete-product/<int:id>', methods=['POST'])
def delete_product(id):
    if session.get('role') != 'superadmin':
        abort(403) # Only Superadmin can delete products
    p = Product.query.get_or_404(id)
    db.session.delete(p)
    db.session.commit()
    return jsonify({"success": True})

@app.route('/admin/download/<filename>')
def download_file(filename):
    if 'role' not in session:
        abort(403)
    return send_from_directory(UPLOAD_DIR, filename)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)