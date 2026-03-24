import os, uuid
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, abort
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, AdminUser, Product, UserUpload, Opportunity, SiteConfig

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:////tmp/feswide_v2026.db')
app.config['SECRET_KEY'] = 'feswide_manual_auth_2026'
db.init_app(app)

# --- AUTO-BOOTSTRAP ---
with app.app_context():
    db.create_all()
    # Corrected Superadmin Credentials
    if not AdminUser.query.filter_by(username='superadmin').first():
        db.session.add(AdminUser(username='superadmin', password='FestusMaster2026!', role='superadmin'))
    
    # Seed Specific Search Keywords
    if not Product.query.first():
        keywords = ["Aether Quality Check", "Aether Code Screening", "Blackbeard", "Blackbeard Multimodal", "Something Big", "Code Review", "Real Coder", "Avalon", "Kobra Clips", "Cacatua Chorus"]
        for kw in keywords:
            db.session.add(Product(name=kw.upper(), filename=f"{kw.lower().replace(' ', '_')}.pdf", description="Verified expert trajectory solutions."))
    db.session.commit()

# --- AUTHENTICATION & IDENTITY ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hex_id = "698b" + uuid.uuid4().hex[:12] # Generate 698b... ID
        user = User(public_id=hex_id, email=request.form.get('email'), full_name=request.form.get('name'), 
                    password=generate_password_hash(request.form.get('password')), is_confirmed=True)
        db.session.add(user); db.session.commit()
        return redirect(url_for('login'))
    return render_template('login.html', mode='register')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email, pwd = request.form.get('email'), request.form.get('password')
        # Check standard user
        u = User.query.filter_by(email=email).first()
        if u and check_password_hash(u.password, pwd):
            session['user_id'] = u.id
            return redirect(url_for('index'))
        # Check Admin/Subadmin
        adm = AdminUser.query.filter_by(username=email, password=pwd).first()
        if adm:
            session['admin_id'], session['role'], session['username'] = adm.id, adm.role, adm.username
            return redirect(url_for('admin'))
        return render_template('login.html', error="Access Denied.", mode='login')
    return render_template('login.html', mode='login')

# --- CORE DASHBOARDS ---

@app.route('/')
def index():
    user = User.query.get(session.get('user_id')) if 'user_id' in session else None
    initials = "".join([n[0] for n in user.full_name.split()]).upper() if user else ""
    query = request.args.get('search', '') # Search Engine Logic
    products = Product.query.filter(Product.name.contains(query.upper())).all() if query else Product.query.all()
    return render_template('index.html', user=user, initials=initials, products=products)

@app.route('/opportunities')
def opportunities():
    user = User.query.get(session.get('user_id')) if 'user_id' in session else None
    return render_template('opportunities.html', user=user)

@app.route('/submit-ai-answer', methods=['POST'])
def submit_ai_answer():
    if 'user_id' not in session: return abort(401)
    db.session.add(UserUpload(user_id=session['user_id'], platform=request.form.get('platform'), 
                              project_name=request.form.get('project'), filename="trajectory.pdf"))
    db.session.commit()
    return jsonify({"message": "Submission Logged under " + User.query.get(session['user_id']).public_id})

@app.route('/admin')
def admin():
    if 'role' not in session: return redirect(url_for('login'))
    return render_template('admin.html', admins=AdminUser.query.all(), products=Product.query.all(), 
                           submissions=db.session.query(UserUpload, User).join(User).all(),
                           role=session['role'], username=session['username'])

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)