import os
from flask import Flask, render_template, request, jsonify, send_from_directory, abort
from models import db, Transaction, UserUpload, User, Product, SearchQuery, ProjectRequest
from werkzeug.utils import secure_filename

app = Flask(__name__, instance_path='/tmp/instance')

# Database Configuration
database_url = os.environ.get('DATABASE_URL', 'sqlite:////tmp/feswide.db')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'feswide_classic_secret')

# File Handling for Vercel
if os.environ.get('VERCEL_ENV'):
    UPLOAD_DIR = '/tmp/uploads'
else:
    UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')

os.makedirs(UPLOAD_DIR, exist_ok=True)
db.init_app(app)

with app.app_context():
    try:
        db.create_all()
        # Seed updated default products
        if not Product.query.first():
            items = [
                Product(name="Aether Multilingual Quality Check", price=999.0, filename="aether.pdf"),
                Product(name="Aether Coder Screening", price=999.0, filename="coder.pdf"),
                Product(name="Kobra Clips", price=999.0, filename="kobra.pdf"),
                Product(name="Grand Prix", price=999.0, filename="grandprix.pdf")
            ]
            db.session.add_all(items)
            db.session.commit()
    except Exception as e:
        print(f"DB Error: {e}")

# --- ROUTES ---

@app.route('/')
def index():
    products = Product.query.all()
    return render_template('index.html', products=products)

@app.route('/api/search')
def api_search():
    q = request.args.get('q', '').lower()
    if not q: return jsonify([])
    
    # Save search query history
    hist = SearchQuery.query.filter_by(query=q).first()
    if hist: hist.search_count += 1
    else: db.session.add(SearchQuery(query=q))
    db.session.commit()

    # Search products and previous queries
    prods = Product.query.filter(Product.name.ilike(f'%{q}%')).all()
    results = [{"name": p.name, "price": p.price} for p in prods]
    
    pops = SearchQuery.query.filter(SearchQuery.query.ilike(f'%{q}%')).limit(3).all()
    for p in pops:
        if not any(r['name'].lower() == p.query for r in results):
            results.append({"name": f"User Search: {p.query}", "price": None})
    return jsonify(results)

@app.route('/request-project', methods=['POST'])
def request_project():
    data = request.json
    db.session.add(ProjectRequest(project_name=data.get('project_name'), platform=data.get('platform')))
    db.session.commit()
    return jsonify({"success": True})

@app.route('/upload-answer', methods=['POST'])
def upload_answer():
    file = request.files.get('file')
    if file and file.filename.endswith('.pdf'):
        fname = secure_filename(file.filename)
        file.save(os.path.join(UPLOAD_DIR, fname))
        new_up = UserUpload(
            uploader_phone="Guest",
            platform=request.form.get('platform'),
            project_name=request.form.get('project_name'),
            mpesa_number=request.form.get('mpesa_number'),
            filename=fname
        )
        db.session.add(new_up)
        db.session.commit()
        return jsonify({"message": "Document sent for manual review!"})
    return jsonify({"error": "Invalid file"}), 400

@app.route('/admin')
def admin_dashboard():
    # Hardcoded role for this demo; usually handled by login sessions
    role = 'superadmin' 
    return render_template('admin.html', 
                           uploads=UserUpload.query.all(), 
                           products=Product.query.all(), 
                           requests=ProjectRequest.query.all(), 
                           role=role)

@app.route('/admin/add-product', methods=['POST'])
def add_product():
    file = request.files.get('file')
    if file:
        fname = secure_filename(file.filename)
        file.save(os.path.join(UPLOAD_DIR, fname))
        db.session.add(Product(name=request.form.get('name'), price=float(request.form.get('price')), filename=fname))
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"success": False}), 400

@app.route('/admin/delete-product/<int:id>', methods=['POST'])
def delete_product(id):
    p = Product.query.get_or_404(id)
    db.session.delete(p)
    db.session.commit()
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(debug=True)