import os
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, session, abort
from models import db, UserUpload, Product, ProjectRequest, AdminUser, ActivityLog
from werkzeug.utils import secure_filename

app = Flask(__name__, instance_path='/tmp/instance')

database_url = os.environ.get('DATABASE_URL', 'sqlite:////tmp/feswide.db')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'feswide_global_secure_2026')

UPLOAD_DIR = '/tmp/uploads' if os.environ.get('VERCEL_ENV') else os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

db.init_app(app)

def log_action(operator, action):
    new_log = ActivityLog(operator=operator, action=action)
    db.session.add(new_log)
    db.session.commit()

with app.app_context():
    db.create_all()
    if not Product.query.first():
        db.session.add_all([
            Product(name="Aether Coder Screening", price=999.0, filename="coder.pdf", description="Verified coding trajectories and detailed rubrics."),
            Product(name="Grand Prix English Evaluation", price=999.0, filename="gp.pdf", description="Comprehensive assessment guidelines and certified answers."),
            Product(name="Kobra Clips Multimodal", price=999.0, filename="kobra.pdf", description="Video and image labeling operational protocols.")
        ])
        db.session.commit()

@app.route('/api/chat', methods=['POST'])
def faith_chat():
    msg = request.json.get('message', '').lower()
    
    if any(word in msg for word in ["hi", "hello", "hey", "greetings"]):
        reply = "Hello! I am Agent Faith, your Feswide Society assistant. How can I help you navigate our repository today?"
    elif any(word in msg for word in ["price", "cost", "pay", "money"]):
        reply = "Our premium modules are available for KES 999. If you are uploading verified answers, we pay contributors KES 500 per approved document."
    elif any(word in msg for word in ["upload", "submit", "contribute"]):
        reply = "You can securely upload your PDF files in the Contributor Hub. Please ensure your M-Pesa number is correct so we can process your payout after the 48-hour review."
    elif any(word in msg for word in ["crack", "missing", "request"]):
        reply = "If a specific project is missing, please submit the exact name in the Request Box. Our engineering team prioritizes these requests and updates the database frequently."
    else:
        reply = "I am processing your request. If you need direct administrative support, please contact our human verification team at support@feswide.com."
    
    return jsonify({"reply": reply})

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
        return jsonify({"status": "success", "message": "Upload successful. Manual review initiated. Payout pending."})
    return jsonify({"status": "error", "message": "Upload failed. Only PDF format is accepted."}), 400

@app.route('/request-project', methods=['POST'])
def request_project():
    data = request.json
    db.session.add(ProjectRequest(project_name=data.get('project_name'), platform=data.get('platform')))
    db.session.commit()
    return jsonify({"status": "success", "message": "Request logged successfully. Check back soon."})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if not AdminUser.query.first():
        db.session.add(AdminUser(username='superadmin', password='FeswideMaster2026!', role='superadmin'))
        db.session.commit()

    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')
        admin_user = AdminUser.query.filter_by(username=u, password=p).first()
        
        if admin_user:
            if not admin_user.is_active:
                return render_template('login.html', error="ACCOUNT SUSPENDED.")
            session['role'] = admin_user.role
            session['username'] = admin_user.username
            log_action(admin_user.username, "Logged into Terminal")
            return redirect(url_for('admin'))
            
        return render_template('login.html', error="ACCESS DENIED. INVALID CREDENTIALS.")
    return render_template('login.html')

@app.route('/admin')
def admin():
    if 'role' not in session: return redirect(url_for('login'))
    return render_template('admin.html', 
                           uploads=UserUpload.query.order_by(UserUpload.id.desc()).all(), 
                           requests=ProjectRequest.query.order_by(ProjectRequest.id.desc()).all(), 
                           products=Product.query.all(),
                           admins=AdminUser.query.all() if session['role'] == 'superadmin' else [],
                           logs=ActivityLog.query.order_by(ActivityLog.id.desc()).limit(50).all() if session['role'] == 'superadmin' else [],
                           role=session['role'],
                           username=session['username'])

@app.route('/admin/approve-upload/<int:id>', methods=['POST'])
def approve_upload(id):
    if 'role' not in session: abort(403)
    upload = UserUpload.query.get_or_404(id)
    upload.status = 'Paid'
    db.session.commit()
    log_action(session['username'], f"Approved payout for project: {upload.project_name}")
    return jsonify({"success": True})

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
    if 'username' in session:
        log_action(session['username'], "Logged out")
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)