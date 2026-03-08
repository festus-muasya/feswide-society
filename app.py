import os
from flask import Flask, render_template, request, jsonify, send_from_directory, abort
from models import db, UserUpload, Product, ProjectRequest, User
from werkzeug.utils import secure_filename

app = Flask(__name__, instance_path='/tmp/instance')

# Database Setup
database_url = os.environ.get('DATABASE_URL', 'sqlite:////tmp/feswide.db')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'feswide_society_official_2026')

# Vercel Temporary Storage
UPLOAD_DIR = '/tmp/uploads' if os.environ.get('VERCEL_ENV') else os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

db.init_app(app)

with app.app_context():
    db.create_all()
    # Initialize default store items
    if not Product.query.first():
        items = [
            Product(name="Aether Multilingual Quality Check", price=999.0, filename="aether.pdf"),
            Product(name="Aether Coder Screening", price=999.0, filename="coder.pdf"),
            Product(name="Kobra Clips", price=999.0, filename="kobra.pdf"),
            Product(name="Grand Prix", price=999.0, filename="grandprix.pdf")
        ]
        db.session.add_all(items)
        db.session.commit()

@app.route('/')
def index():
    products = Product.query.all()
    return render_template('index.html', products=products)

@app.route('/api/chat', methods=['POST'])
def faith_chat():
    user_msg = request.json.get('message', '').lower()
    # Agent Faith Knowledge Base
    if "hello" in user_msg or "hi" in user_msg:
        reply = "Welcome to Feswide Society. I am Agent Faith. I can help with Outlier or Handshake answers."
    elif "price" in user_msg or "cost" in user_msg:
        reply = "Our modules are KES 999/=. We pay contributors KES 500/= per verified PDF."
    elif "upload" in user_msg:
        reply = "You can upload answers in the Contributor Hub. Review takes 48 hours."
    elif "crack" in user_msg or "request" in user_msg:
        reply = "Use the Vote Box to request a project. We crack them within 48 hours."
    else:
        reply = "For further assistance, please contact our support team at support@feswide.com."
    return jsonify({"reply": reply})

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
        return jsonify({"message": "Submitted! Payout processed after 48hr manual review."})
    return jsonify({"error": "PDF file is required."}), 400

@app.route('/request-project', methods=['POST'])
def request_project():
    data = request.json
    db.session.add(ProjectRequest(project_name=data.get('project_name'), platform=data.get('platform')))
    db.session.commit()
    return jsonify({"success": True})

@app.route('/admin')
def admin():
    # Role-based restriction logic
    uploads = UserUpload.query.all()
    products = Product.query.all()
    requests = ProjectRequest.query.all()
    return render_template('admin.html', uploads=uploads, products=products, requests=requests, role='superadmin')

if __name__ == '__main__':
    app.run(debug=True)