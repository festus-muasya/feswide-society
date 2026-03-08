import os
from flask import Flask, render_template, request, jsonify, send_from_directory, abort
from models import db, Transaction, UserUpload, User, Product, SearchQuery
from werkzeug.utils import secure_filename

app = Flask(__name__, instance_path='/tmp/instance')

database_url = os.environ.get('DATABASE_URL', 'sqlite:////tmp/feswide.db')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback_secret_key_123')

# File Storage for Vercel
if os.environ.get('VERCEL_ENV') or os.environ.get('VERCEL_URL'):
    UPLOAD_DIR = '/tmp/uploads'
else:
    UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')

os.makedirs(UPLOAD_DIR, exist_ok=True)
db.init_app(app)

with app.app_context():
    try:
        db.create_all()
        # Seed some default products if the store is empty
        if not Product.query.first():
            p1 = Product(name="Aether Multilingual Quality Check", price=999.00, filename="aether_module.pdf")
            p2 = Product(name="Aether Coder Screening Module", price=999.00, filename="coder_module.pdf")
            db.session.add_all([p1, p2])
            db.session.commit()
    except Exception as e:
        print(f"DATABASE ERROR: {e}")

# --- PUBLIC ROUTES ---
@app.route('/')
def index():
    products = Product.query.all()
    return render_template('index.html', products=products)

@app.route('/api/search')
def api_search():
    query = request.args.get('q', '').lower()
    if not query:
        return jsonify([])
    
    # Save the search query for future users
    existing_search = SearchQuery.query.filter_by(query=query).first()
    if existing_search:
        existing_search.search_count += 1
    else:
        new_search = SearchQuery(query=query)
        db.session.add(new_search)
    db.session.commit()

    # Find matching products
    matches = Product.query.filter(Product.name.ilike(f'%{query}%')).limit(5).all()
    results = [{"name": p.name, "price": p.price} for p in matches]
    
    # Add popular user searches to suggestions
    popular = SearchQuery.query.filter(SearchQuery.query.ilike(f'%{query}%')).order_by(SearchQuery.search_count.desc()).limit(3).all()
    for pop in popular:
        if not any(r['name'].lower() == pop.query for r in results):
            results.append({"name": f"Other users searched: {pop.query}", "price": None})

    return jsonify(results)

@app.route('/pay-stk', methods=['POST'])
def pay_stk():
    data = request.json
    mock_checkout_id = "ws_CO_1234567890" 
    new_txn = Transaction(checkout_request_id=mock_checkout_id, phone=data.get('phone'), amount=data.get('amount'), document_name=data.get('item'))
    db.session.add(new_txn)
    db.session.commit()
    return jsonify({"status": "PROMPTED", "checkoutId": mock_checkout_id})

@app.route('/upload-answer', methods=['POST'])
def upload_answer():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    platform = request.form.get('platform')
    project_name = request.form.get('project_name')
    
    if file and file.filename.endswith('.pdf'):
        filename = secure_filename(file.filename)
        file.save(os.path.join(UPLOAD_DIR, filename))
        new_upload = UserUpload(uploader_phone="Guest User", platform=platform, project_name=project_name, filename=filename)
        db.session.add(new_upload)
        db.session.commit()
        return jsonify({"message": f"{project_name} successfully sent to Admin Dashboard!"})
    return jsonify({"error": "Invalid file type. Must be PDF."}), 400

# --- ADMIN ROUTES ---
@app.route('/admin')
def admin_dashboard():
    # Simulating a logged-in user role for demonstration (Change to 'subadmin' to test restrictions)
    current_role = 'superadmin' 
    uploads = UserUpload.query.order_by(UserUpload.id.desc()).all()
    users = User.query.all()
    products = Product.query.all()
    return render_template('admin.html', uploads=uploads, users=users, products=products, role=current_role)

@app.route('/admin/add-product', methods=['POST'])
def add_product():
    name = request.form.get('name')
    price = request.form.get('price')
    file = request.files['file']
    
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(UPLOAD_DIR, filename))
        new_prod = Product(name=name, price=float(price), filename=filename)
        db.session.add(new_prod)
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"success": False}), 400

@app.route('/admin/delete-product/<int:prod_id>', methods=['POST'])
def delete_product(prod_id):
    prod = Product.query.get_or_404(prod_id)
    db.session.delete(prod)
    db.session.commit()
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(debug=True)