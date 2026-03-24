import os, uuid, secrets
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, abort
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, AdminUser, Product, UserUpload
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:////tmp/feswide_v31.db')
app.config['SECRET_KEY'] = 'feswide_ultra_2026_opsec'
db.init_app(app)

# --- EMAIL HELPER ---
def send_reset_email(user_email, token):
    """Sends the recovery link via SendGrid API"""
    reset_url = url_for('reset_password', token=token, _external=True)
    message = Mail(
        from_email=os.environ.get('FROM_EMAIL', 'ops@feswide.com'),
        to_emails=user_email,
        subject='Feswide Society: Identity Recovery',
        html_content=f'<p>Use this secure link to reset your passkey: <a href="{reset_url}">{reset_url}</a>. Link expires in 1 hour.</p>'
    )
    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        sg.send(message)
    except Exception as e:
        print(f"MAIL_ERROR: {e}")

# --- AUTO-BOOTSTRAP ---
with app.app_context():
    db.create_all()
    if not AdminUser.query.filter_by(username='superadmin').first():
        db.session.add(AdminUser(username='superadmin', password='FestusMaster2026!', role='superadmin'))
    db.session.commit()

# --- LOGIN & OPS ROUTES ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = User.query.filter_by(email=request.form.get('email')).first()
        if u and check_password_hash(u.password, request.form.get('password')):
            session['user_id'] = u.id; return redirect(url_for('index'))
        return render_template('login.html', error="Invalid User Credentials", mode='login')
    return render_template('login.html', mode='login')

@app.route('/ops-login', methods=['GET', 'POST'])
def ops_login():
    if request.method == 'POST':
        adm = AdminUser.query.filter_by(username=request.form.get('u'), password=request.form.get('p')).first()
        if adm:
            session['admin_id'], session['role'], session['username'] = adm.id, adm.role, adm.username
            return redirect(url_for('admin'))
        return render_template('ops_login.html', error="Unauthorized Access")
    return render_template('ops_login.html')

# --- PASSWORD RECOVERY FLOW ---

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email')).first()
        if user:
            token = secrets.token_urlsafe(32)
            user.reset_token, user.token_expiry = token, datetime.utcnow() + timedelta(hours=1)
            db.session.commit()
            send_reset_email(user.email, token) # Actual send logic
            return render_template('forgot.html', success="Check your inbox for recovery instructions.")
        return render_template('forgot.html', error="Identity not found.")
    return render_template('forgot.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    if not user or user.token_expiry < datetime.utcnow():
        return render_template('forgot.html', error="Recovery link expired or invalid.")
    if request.method == 'POST':
        user.password = generate_password_hash(request.form.get('password'))
        user.reset_token = user.token_expiry = None # Clear token
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('reset_form.html', token=token)

# --- GOOGLE AUTH ---
@app.route('/auth/google')
def google_auth():
    mock_email = "contributor_v26@gmail.com"
    user = User.query.filter_by(email=mock_email).first()
    if not user:
        user = User(public_id="698b"+uuid.uuid4().hex[:12], email=mock_email, full_name="Google Contributor")
        db.session.add(user); db.session.commit()
    session['user_id'] = user.id
    return redirect(url_for('index'))

@app.route('/')
def index():
    user = User.query.get(session.get('user_id')) if 'user_id' in session else None
    initials = "".join([n[0] for n in user.full_name.split()]).upper() if user else ""
    return render_template('index.html', user=user, initials=initials, products=Product.query.all())

@app.route('/admin')
def admin():
    if 'role' not in session: return abort(403)
    subs = db.session.query(UserUpload, User).join(User).all()
    return render_template('admin.html', role=session['role'], submissions=subs, admins=AdminUser.query.all())

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)