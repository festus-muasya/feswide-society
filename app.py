import os, uuid
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, abort
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, AdminUser, Product, UserUpload, Opportunity

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:////tmp/feswide_v4.db')
app.config['SECRET_KEY'] = 'feswide_master_2026_secure'
db.init_app(app)

with app.app_context():
    db.create_all()
    # Fixed Superadmin
    if not AdminUser.query.filter_by(username='superadmin').first():
        db.session.add(AdminUser(username='superadmin', password='FestusMaster2026!', role='superadmin'))
    
    # Seeding Repository
    if not Product.query.first():
        names = ["Aether Quality Check", "Blackbeard Multimodal", "Kobra Clips", "Cacatua Chorus", "Avalon Code Review", "Something Big"]
        for n in names:
            db.session.add(Product(name=n, filename=f"{n.lower().replace(' ', '_')}.pdf"))
    db.session.commit()

# --- REDIRECTS ---

@app.route('/proxy')
def proxy_redirect():
    """Direct Switch to Shadowmax Proxy"""
    return redirect("https://shadowmaxproxy.com")

@app.route('/jobs')
def jobs():
    hiring = Opportunity.query.filter_by(category='Hiring').all()
    tasks = Opportunity.query.filter_by(category='Tasking').all()
    return render_template('jobs.html', hiring=hiring, tasks=tasks)

# --- CORE ROUTES ---

@app.route('/')
def index():
    user = User.query.get(session.get('user_id')) if 'user_id' in session else None
    initials = "".join([n[0] for n in user.full_name.split()]).upper() if user else "OP"
    query = request.args.get('search', '')
    products = Product.query.filter(Product.name.contains(query.upper())).all() if query else Product.query.all()
    return render_template('index.html', user=user, initials=initials, products=products)

@app.route('/opportunities', methods=['GET', 'POST'])
def opportunities():
    if request.method == 'POST':
        new_opp = Opportunity(
            category=request.form.get('category'),
            role=request.form.get('role'),
            platform=request.form.get('platform'),
            description=request.form.get('desc'),
            contact=request.form.get('contact')
        )
        db.session.add(new_opp); db.session.commit()
        return redirect(url_for('jobs'))
    return render_template('opportunities.html')

@app.route('/ops-login', methods=['GET', 'POST'])
def ops_login():
    if request.method == 'POST':
        adm = AdminUser.query.filter_by(username=request.form.get('u'), password=request.form.get('p')).first()
        if adm:
            session['admin_id'], session['role'], session['username'] = adm.id, adm.role, adm.username
            return redirect(url_for('admin'))
    return render_template('ops_login.html')

@app.route('/admin')
def admin():
    if 'role' not in session: return abort(403)
    return render_template('admin.html', 
                           products=Product.query.all(), 
                           users=User.query.all(),
                           opps=Opportunity.query.all(),
                           submissions=db.session.query(UserUpload, User).join(User).all())
# Seed Repository with specific requested projects
if not Product.query.first():
    projects = [
        "OpenClaw",
        "Blackbeard",
        "Aether",
        "Millenium Leaf",
        "Code Review",
        "Real Coder",
        "Aether 🔥" # Long run project designation
    ]
    for name in projects:
        db.session.add(Product(name=name, price=999.0, filename=f"{name.lower().replace(' ', '_')}.pdf"))
db.session.commit()

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)