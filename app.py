import os, uuid, secrets
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, abort, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, AdminUser, Product, UserUpload, Opportunity
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:////tmp/feswide_v2026_final.db')
app.config['SECRET_KEY'] = 'feswide_ultra_opsec_2026'
db.init_app(app)

# --- SYSTEM INITIALIZATION ---
with app.app_context():
    db.create_all()
    if not AdminUser.query.filter_by(username='superadmin').first():
        db.session.add(AdminUser(username='superadmin', password='FestusMaster2026!', role='superadmin'))
    
    if not Product.query.first():
        projects = ["OpenClaw", "Blackbeard", "Aether", "Millenium Leaf", "Code Review", "Real Coder", "Aether 🔥"]
        for name in projects:
            db.session.add(Product(name=name, price=999.0, filename=f"{name.lower().replace(' ', '_')}.pdf"))
    db.session.commit()

# --- REDIRECTS & JOBS ---

@app.route('/proxy')
def proxy_redirect():
    """Switch to Shadowmax Proxy"""
    return redirect("https://shadowmaxproxy.com")

@app.route('/jobs')
def jobs():
    hiring = Opportunity.query.filter_by(category='Hiring').all()
    tasks = Opportunity.query.filter_by(category='Tasking').all()
    return render_template('jobs.html', hiring=hiring, tasks=tasks)

@app.route('/opportunities', methods=['GET', 'POST'])
def opportunities():
    if request.method == 'POST':
        opp = Opportunity(category=request.form.get('category'), role=request.form.get('role'),
                          platform=request.form.get('platform'), description=request.form.get('desc'),
                          contact=request.form.get('contact'))
        db.session.add(opp); db.session.commit()
        return redirect(url_for('jobs'))
    return render_template('opportunities.html')

# --- AUTHENTICATION ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = User.query.filter_by(email=request.form.get('email')).first()
        if u and check_password_hash(u.password, request.form.get('password')):
            session['user_id'] = u.id; return redirect(url_for('index'))
    return render_template('login.html', mode='login')

@app.route('/ops-login', methods=['GET', 'POST'])
def ops_login():
    if request.method == 'POST':
        adm = AdminUser.query.filter_by(username=request.form.get('u'), password=request.form.get('p')).first()
        if adm:
            session['admin_id'], session['role'], session['username'] = adm.id, adm.role, adm.username
            return redirect(url_for('admin'))
    return render_template('ops_login.html')

@app.route('/auth/google')
def google_auth():
    mock_email = "operator_sso@gmail.com"
    user = User.query.filter_by(email=mock_email).first()
    if not user:
        user = User(public_id="698b"+uuid.uuid4().hex[:12], email=mock_email, full_name="Google Operator")
        db.session.add(user); db.session.commit()
    session['user_id'] = user.id; return redirect(url_for('index'))

# --- ADMIN CONTROL ---

@app.route('/admin')
def admin():
    if 'role' not in session: return abort(403)
    return render_template('admin.html', role=session['role'], products=Product.query.all(),
                           users=User.query.all(), opps=Opportunity.query.all(),
                           submissions=db.session.query(UserUpload, User).join(User).all())

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)