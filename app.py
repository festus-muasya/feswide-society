import os, uuid
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, abort
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, AdminUser, Product, UserUpload, SiteConfig

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:////tmp/feswide_v25.db')
app.config['SECRET_KEY'] = 'feswide_manual_auth_2026'
db.init_app(app)

with app.app_context():
    db.create_all()
    # Initialize Superadmin
    if not AdminUser.query.filter_by(username='superadmin').first():
        db.session.add(AdminUser(username='superadmin', password='FeswideMaster2026!', role='superadmin'))
    
    # Seed Specific Search Keywords
    if not Product.query.first():
        keywords = ["Aether Quality Check", "Aether Code Screening", "Blackbeard", "Blackbeard Multimodal", "Something Big", "Code Review", "Real Coder", "Avalon", "Kobra Clips", "Cacatua Chorus"]
        for kw in keywords:
            db.session.add(Product(name=kw.upper(), filename=f"{kw.lower().replace(' ', '_')}.pdf", description="Verified expert trajectory solutions."))
    db.session.commit()

# --- AUTH ROUTES ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hex_id = "698b" + uuid.uuid4().hex[:12]
        user = User(public_id=hex_id, email=request.form.get('email'), full_name=request.form.get('name'), password=generate_password_hash(request.form.get('password')))
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('login.html', mode='register')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = User.query.filter_by(email=request.form.get('email')).first()
        if u and check_password_hash(u.password, request.form.get('password')):
            session['user_id'] = u.id
            return redirect(url_for('index'))
    return render_template('login.html', mode='login')

@app.route('/auth/google')
def google_auth():
    """Placeholder for Google Auto-registration"""
    # Logic for Google OAuth2 would go here
    return redirect(url_for('index'))

# --- CORE LOGIC ---

@app.route('/')
def index():
    user = User.query.get(session.get('user_id')) if 'user_id' in session else None
    initials = "".join([n[0] for n in user.full_name.split()]).upper() if user else ""
    query = request.args.get('search', '')
    if query:
        products = Product.query.filter(Product.name.contains(query.upper())).all()
    else:
        products = Product.query.all()
    return render_template('index.html', user=user, initials=initials, products=products)

@app.route('/opportunities')
def opportunities():
    user = User.query.get(session.get('user_id')) if 'user_id' in session else None
    return render_template('opportunities.html', user=user)

@app.route('/admin')
def admin_dashboard():
    if session.get('role') not in ['superadmin', 'subadmin']: return abort(403)
    subs = db.session.query(UserUpload, User).join(User).all()
    return render_template('admin.html', submissions=subs, products=Product.query.all(), admins=AdminUser.query.all())

@app.route('/admin/del-answer/<int:id>')
def del_answer(id):
    Product.query.filter_by(id=id).delete()
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)