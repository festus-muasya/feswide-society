import os, uuid, secrets
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, abort, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, AdminUser, Product, UserUpload, Opportunity
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

app = Flask(__name__)

# --- DATABASE & SECURITY CONFIG ---
database_url = os.environ.get('DATABASE_URL', 'sqlite:////tmp/feswide_v2026_master.db')
if database_url.startswith("postgres://"): 
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'feswide_opsec_master_2026')

# Session Hardening
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True

db.init_app(app)

# --- EMAIL RECOVERY HELPER ---
def send_reset_email(user_email, token):
    """Dispatches secure recovery link via SendGrid"""
    reset_url = url_for('reset_password', token=token, _external=True)
    message = Mail(
        from_email=os.environ.get('FROM_EMAIL', 'ops@feswide.ru'),
        to_emails=user_email,
        subject='FESWIDE SOCIETY: Identity Recovery Terminal',
        html_content=f'<p>Access your secure recovery terminal here: <a href="{reset_url}">{reset_url}</a>. Link expires in 60 minutes.</p>'
    )
    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        sg.send(message)
    except Exception as e:
        print(f"MAIL_SERVER_ERROR: {e}")

# --- SYSTEM BOOTSTRAP ---
with app.app_context():
    db.create_all()
    # Initialize Superadmin: username=superadmin, pwd=FestusMaster2026!
    if not AdminUser.query.filter_by(username='superadmin').first():
        db.session.add(AdminUser(username='superadmin', password='FestusMaster2026!', role='superadmin'))
    
    # Seed Repository: Title Case, No Descriptions
    if not Product.query.first():
        items = ["Aether Quality Check", "Blackbeard Multimodal", "Kobra Clips", "Cacatua Chorus", "Avalon Code Review", "Something Big"]
        for name in items:
            db.session.add(Product(name=name, filename=f"{name.lower().replace(' ', '_')}.pdf", description=""))
    db.session.commit()

# ==========================================
# 1. AUTHENTICATION & IDENTITY
# ==========================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hex_id = "698b" + uuid.uuid4().hex[:12]
        user = User(public_id=hex_id, email=request.form.get('email'), full_name=request.form.get('name'),
                    password=generate_password_hash(request.form.get('password')))
        db.session.add(user); db.session.commit()
        return redirect(url_for('login'))
    return render_template('login.html', mode='register')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Standard User Portal"""
    if request.method == 'POST':
        u = User.query.filter_by(email=request.form.get('email')).first()
        if u and check_password_hash(u.password, request.form.get('password')):
            session['user_id'] = u.id; return redirect(url_for('index'))
        return render_template('login.html', error="Invalid User Credentials", mode='login')
    return render_template('login.html', mode='login')

@app.route('/ops-login', methods=['GET', 'POST'])
def ops_login():
    """Restricted Admin Terminal"""
    if request.method == 'POST':
        adm = AdminUser.query.filter_by(username=request.form.get('u'), password=request.form.get('p')).first()
        if adm:
            session['admin_id'], session['role'], session['username'] = adm.id, adm.role, adm.username
            return redirect(url_for('admin'))
        return render_template('ops_login.html', error="Unauthorized Operator Access")
    return render_template('ops_login.html')

@app.route('/auth/google')
def google_auth():
    """Simulation of Google Auto-registration with 698b ID"""
    mock_email = "contributor_google@gmail.com"
    user = User.query.filter_by(email=mock_email).first()
    if not user:
        user = User(public_id="698b"+uuid.uuid4().hex[:12], email=mock_email, full_name="Google Contributor")
        db.session.add(user); db.session.commit()
    session['user_id'] = user.id
    return redirect(url_for('index'))

# ==========================================
# 2. PASSWORD RECOVERY
# ==========================================

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email')).first()
        if user:
            token = secrets.token_urlsafe(32)
            user.reset_token, user.token_expiry = token, datetime.utcnow() + timedelta(hours=1)
            db.session.commit()
            send_reset_email(user.email, token)
            return render_template('forgot.html', success="Recovery link dispatched to your email.")
        return render_template('forgot.html', error="Identity not found.")
    return render_template('forgot.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    if not user or user.token_expiry < datetime.utcnow():
        return render_template('forgot.html', error="Recovery link has expired.")
    if request.method == 'POST':
        user.password = generate_password_hash(request.form.get('password'))
        user.reset_token = user.token_expiry = None
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('reset_form.html', token=token)

# ==========================================
# 3. CORE PLATFORM
# ==========================================

@app.route('/')
def index():
    user = User.query.get(session.get('user_id')) if 'user_id' in session else None
    initials = "".join([n[0] for n in user.full_name.split()]).upper() if user and user.full_name else "OP"
    query = request.args.get('search', '') # Search engine logic
    products = Product.query.filter(Product.name.contains(query.upper())).all() if query else Product.query.all()
    return render_template('index.html', user=user, initials=initials, products=products)

@app.route('/download/<filename>')
def download_file(filename):
    """Serves secure trajectories from vault"""
    directory = os.path.join(app.root_path, 'static', 'vault')
    return send_from_directory(directory, filename, as_attachment=True)

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

# ==========================================
# 4. ADMIN CONTROL CENTER
# ==========================================

@app.route('/admin')
def admin():
    if 'role' not in session: return redirect(url_for('ops_login'))
    return render_template('admin.html', admins=AdminUser.query.all(), products=Product.query.all(), 
                           submissions=db.session.query(UserUpload, User).join(User).all(),
                           role=session['role'], username=session['username'])

@app.route('/admin/del-answer/<int:id>')
def del_answer(id):
    if session.get('role') != 'superadmin': abort(403)
    Product.query.filter_by(id=id).delete(); db.session.commit()
    return redirect(url_for('admin'))

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)