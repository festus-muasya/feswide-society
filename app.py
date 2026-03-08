import os
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, session, abort
from models import db, UserUpload, Product, ProjectRequest, User
from werkzeug.utils import secure_filename

app = Flask(__name__, instance_path='/tmp/instance')

database_url = os.environ.get('DATABASE_URL', 'sqlite:////tmp/feswide.db')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'feswide_high_security_2026')

UPLOAD_DIR = '/tmp/uploads' if os.environ.get('VERCEL_ENV') else os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

db.init_app(app)

with app.app_context():
    db.create_all()
    if not Product.query.first():
        db.session.add_all([
            Product(name="Aether Coder Screening", price=999.0, filename="coder.pdf", description="Verified coding trajectories and rubrics."),
            Product(name="Grand Prix English Evaluation", price=999.0, filename="gp.pdf", description="Comprehensive assessment guidelines and answers."),
            Product(name="Kobra Clips Multimodal", price=999.0, filename="kobra.pdf", description="Video and image labeling operational protocols.")
        ])
        db.session.commit()

@app.route('/api/chat', methods=['POST'])
def faith_chat():
    msg = request.json.get('message', '').lower()
    if any(w in msg for w in ["hi", "hello", "hey"]):
        reply = "Hello there. I am Agent Faith. How can I assist you with our repository today?"
    elif any(w in msg for w in ["price", "cost", "pay"]):
        reply = "Premium crack modules are KES 999. We pay contributors KES 500 per verified PDF submission."
    elif any(w in msg for w in ["upload", "submit"]):
        reply = "Securely upload Handshake/Outlier PDFs via the Contributor Hub. M-Pesa payouts follow a 48hr review."
    elif any(w in msg for w in ["crack", "vote", "request"]):
        reply = "Log missing projects in the Vote Box. High-demand projects are cracked within 48 hours."
    else:
        reply = "Processing request... For administrative override, email support@feswide.com."
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
        return jsonify({"status": "success", "message": "UPLOAD SUCCESSFUL. Payout pending 48hr manual review."})
    return jsonify({"status": "error", "message": "UPLOAD FAILED. Only PDF format is accepted."}), 400

@app.route('/request-project', methods=['POST'])
def request_project():
    data = request.json
    db.session.add(ProjectRequest(project_name=data.get('project_name'), platform=data.get('platform')))
    db.session.commit()
    return jsonify({"status": "success", "message": "REQUEST LOGGED. Check back in 48 hours."})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('username'), request.form.get('password')
        if u == 'superadmin' and p == 'FeswideMaster2026!':
            session['role'] = 'superadmin'
            return redirect(url_for('admin'))
        elif u == 'subadmin' and p == 'FeswideStaff!':
            session['role'] = 'subadmin'
            return redirect(url_for('admin'))
        return render_template('login.html', error="ACCESS DENIED. INVALID CREDENTIALS.")
    return render_template('login.html', error=None)

@app.route('/admin')
def admin():
    if 'role' not in session: return redirect(url_for('login'))
    return render_template('admin.html', 
                           uploads=UserUpload.query.order_by(UserUpload.id.desc()).all(), 
                           requests=ProjectRequest.query.order_by(ProjectRequest.id.desc()).all(), 
                           products=Product.query.all(),
                           role=session['role'])

@app.route('/admin/add-product', methods=['POST'])
def add_product():
    if session.get('role') != 'superadmin': abort(403)
    file = request.files.get('file')
    if file and file.filename.endswith('.pdf'):
        fname = secure_filename(file.filename)
        file.save(os.path.join(UPLOAD_DIR, fname))
        db.session.add(Product(name=request.form.get('name'), price=float(request.form.get('price')), description=request.form.get('description'), filename=fname))
        db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/delete-product/<int:id>', methods=['POST'])
def delete_product(id):
    if session.get('role') != 'superadmin': abort(403)
    db.session.delete(Product.query.get_or_404(id))
    db.session.commit()
    return jsonify({"success": True})

@app.route('/admin/download/<filename>')
def download_file(filename):
    if 'role' not in session: abort(403)
    return send_from_directory(UPLOAD_DIR, filename)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)