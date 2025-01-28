import smtplib
from functools import wraps
import time
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import Nullable
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from werkzeug.utils import secure_filename

DB_DIR = "db.db"
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_DIR}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

app.secret_key = 'APP_SECRET_KEY'
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth"

class Role(db.Model):
    Id = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(50), nullable=False)
    users = db.relationship('User', backref='role', lazy=True)

    def __repr__(self) -> str:
        return f'<UserId>: {self.Id}; <Name>: {self.Name}'

class Company(db.Model):
    Id = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(20), nullable=False)
    advertisements = db.relationship('Advertisement', backref='company', lazy=True)
    user = db.relationship('User', backref='company', uselist=False)

class User(UserMixin, db.Model):
    Id = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(50), nullable=False)
    Email = db.Column(db.String(50), nullable=False)
    Password = db.Column(db.String(50), nullable=False)
    RoleId = db.Column(db.Integer, db.ForeignKey('role.Id'), nullable=True)
    CompanyId = db.Column(db.Integer, db.ForeignKey('company.Id'), nullable=True)

    def get_id(self):
        return str(self.Id)

class User_Applied_Company(db.Model):
    Id = db.Column(db.Integer, primary_key=True)
    UserId = db.Column(db.Integer, db.ForeignKey('user.Id'), nullable=False)
    AdvertisementId = db.Column(db.Integer, db.ForeignKey('advertisement.Id'), nullable=False)
    CV_Path = db.Column(db.String(255), nullable=False)
    ApplyDate = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('applications', lazy=True))

class Advertisement(db.Model):
    Id = db.Column(db.Integer, primary_key=True)
    Title = db.Column(db.String(20), nullable=False)
    Description = db.Column(db.String(300), nullable=False)
    Position = db.Column(db.String(20), nullable=False)
    CompanyId = db.Column(db.Integer, db.ForeignKey('company.Id'), nullable=False)
    applications = db.relationship('User_Applied_Company', 
                                 backref='advertisement',
                                 cascade='all, delete-orphan',
                                 lazy=True)

with app.app_context():
    db.create_all()

with app.app_context():
    if not Role.query.first():
        role_hire = Role(Id=1,Name="Hire")
        role_applicant = Role(Id=2,Name="Applicant")
        db.session.add_all([role_hire, role_applicant])
        db.session.commit()
    if not Company.query.first():
        db.session.add_all([Company(Name="Company1"),Company(Name="Company2")])
        db.session.commit()
    if not User.query.first():
        db.session.add_all([
            User(Name="Admin",Email="admin1@gmail.com",Password="admin1",RoleId=1,CompanyId=1),
            User(Name="Admin2",Email="admin2@gmail.com",Password="admin2",RoleId=1,CompanyId=2),
        ])
        db.session.commit()

def role_required(required_role_name):
    def wrapper(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            if current_user.role.Name != required_role_name:
                flash("You do not have permission to access this page.", "warning")
                return redirect(url_for('home'))
            return func(*args, **kwargs)
        return wrapped
    return wrapper
    
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/")
def home():
    layout = "layout_guest.html"
    if current_user.is_authenticated and current_user.role:
        if current_user.role.Name == "Applicant":
            layout = "layout_user.html"
            
            company_id = request.args.get('company_id', type=int)
            selected_company = None
            
            query = Advertisement.query\
                .join(Company, Advertisement.CompanyId == Company.Id)\
                .add_columns(
                    Advertisement.Id,
                    Advertisement.Title,
                    Advertisement.Description,
                    Advertisement.Position,
                    Company.Name.label('company_name')
                )
            
            if company_id:
                query = query.filter(Company.Id == company_id)
                selected_company = Company.query.get_or_404(company_id)
            companies = Company.query.all()
            all_ads = query.all()
            
            return render_template(
                "home.html", 
                title="Home", 
                layout=layout, 
                ads=all_ads,
                companies=companies,
                selected_company=selected_company
            )
            
        elif current_user.role.Name == "Hire":
            layout = "layout_company.html"
            company_ads = Advertisement.query.filter_by(CompanyId=current_user.CompanyId).all()
            return render_template("home.html", title="Home", layout=layout, company_ads=company_ads)
    
    return render_template("home.html", title="Home", layout=layout)

@app.route("/about",methods=["GET"])
def about():
    layout = "layout_guest.html"
    return render_template("about.html",title="About",layout=layout)

@app.route("/contact", methods=["GET", "POST"])
def contact():
    layout = "layout_guest.html"
    alert = None
    alert_type = None
    if request.method == "POST":
        email = request.form['email']
        subject = request.form['subject']
        message = request.form['message']
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        receiver_email = "RECEIVER_ADRESS"
        receiver_passwd = "YOUR_GMAIL_APP_KEY"
        try:
            msg = MIMEMultipart()
            msg['From'] = email
            msg['To'] = receiver_email
            msg['Subject'] = f"Yeni İletişim Formu: {subject}"
            body = f"Gönderen: {email}\n\nMesaj:\n{message}"
            msg.attach(MIMEText(body, 'plain'))
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(receiver_email, receiver_passwd)
                server.sendmail(email, receiver_email, msg.as_string())
            alert = "Mesajınız başarıyla gönderildi!"
            alert_type = "success"
        except Exception as e:
            alert = f"E-posta gönderimi sırasında bir hata oluştu: {e}"
            alert_type = "danger"
    return render_template("contact.html", layout=layout, alert=alert, alert_type=alert_type)

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form["email_login"]
        password = request.form["password_login"]
        user = User.query.filter_by(Email=email).first()
        if user and user.Password == password:
            login_user(user)
            return redirect(url_for('home'))
        flash("Invalid credentials. Please check your email and password.", "danger")
        return redirect(url_for("login"))
    else:
        if current_user.is_authenticated:
            return redirect(url_for('home'))
        layout = "layout_guest.html"
        return render_template("login.html", title="Login", layout=layout)

@app.route("/register",methods=["GET","POST"])
def register():
    if request.method == "POST":
        name = request.form['name_field']
        email = request.form['email_field']
        password = request.form['password_field']
        new_user = User(Name=name, Email=email, Password=password, RoleId=2)
        db.session.add(new_user)
        db.session.commit()
        return redirect("/login")
    else:
        layout = "layout_guest.html"
        return render_template("register.html",layout=layout)

@app.route("/publish_add", methods=["GET", "POST"])
@login_required
def publish_adveristment():
    if request.method == "POST":
        title = request.form['title']
        description = request.form['description']
        position = request.form['position']
        company_id = current_user.CompanyId
        new_add = Advertisement(Title=title, Description=description, Position=position, CompanyId=company_id)
        db.session.add(new_add)
        db.session.commit()
        return redirect(url_for("home"))
    else:
        return render_template("publish_add.html", title="Publish Advertisement", layout="layout_company.html")

@app.route("/edit_ad/<int:ad_id>", methods=["GET", "POST"])
@login_required
def edit_ad(ad_id):
    ad = Advertisement.query.get_or_404(ad_id)
    if ad.CompanyId != current_user.CompanyId:
        flash("You do not have permission to edit this advertisement.", "warning")
        return redirect(url_for("home"))
    
    if request.method == "POST":
        ad.Title = request.form['title']
        ad.Description = request.form['description']
        ad.Position = request.form['position']
        db.session.commit()
        flash("Advertisement updated successfully!", "success")
        return redirect(url_for("home"))
    return render_template("edit_ad.html", ad=ad, title="Edit Advertisement", layout="layout_company.html")

@app.route("/delete_ad/<int:ad_id>", methods=["POST"])
@login_required
def delete_ad(ad_id):
    ad = Advertisement.query.get_or_404(ad_id)
    if ad.CompanyId != current_user.CompanyId:
        flash("You do not have permission to delete this advertisement.", "warning")
        return redirect(url_for("home"))
    try:
        db.session.delete(ad)
        db.session.commit()
        flash("Advertisement and related applications deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred while deleting the advertisement: {str(e)}", "danger")
    
    return redirect(url_for("home"))

@app.route("/apply", methods=["POST"])
@login_required
def apply():
    try:
        ad_id = request.form.get('ad_id')
        if not ad_id:
            flash('Invalid advertisement ID.', 'danger')
            return redirect(url_for('home'))
            
        try:
            ad_id = int(ad_id)
        except ValueError:
            flash('Invalid advertisement ID format.', 'danger')
            return redirect(url_for('home'))

        advertisement = Advertisement.query.get(ad_id)
        if not advertisement:
            flash('Advertisement not found.', 'danger')
            return redirect(url_for('home'))
        
        existing_application = User_Applied_Company.query.filter_by(
            UserId=current_user.Id, 
            AdvertisementId=ad_id
        ).first()
        
        if existing_application:
            flash('You have already applied for this position.', 'warning')
            return redirect(url_for('home'))

        if 'cv' not in request.files:
            flash('Please upload your CV.', 'danger')
            return redirect(url_for('home'))

        file = request.files['cv']
        if file.filename == '':
            flash('No file selected.', 'danger')
            return redirect(url_for('home'))

        allowed_extensions = {'pdf', 'doc', 'docx'}
        if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
            flash('Only PDF, DOC, and DOCX files are allowed.', 'danger')
            return redirect(url_for('home'))

        UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads', 'cvs')
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = secure_filename(f"cv_{current_user.Id}_{ad_id}_{timestamp}_{file.filename}")
        file_path = os.path.join(UPLOAD_FOLDER, safe_filename)
        
        file.save(file_path)

        new_application = User_Applied_Company(
            UserId=current_user.Id,
            AdvertisementId=ad_id,
            CV_Path=file_path,
            ApplyDate=datetime.utcnow()
        )
        
        db.session.add(new_application)
        db.session.commit()

        flash('Your application has been submitted successfully!', 'success')
        return redirect(url_for('home'))

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error in apply route: {str(e)}")
        flash('An error occurred while submitting your application. Please try again.', 'danger')
        return redirect(url_for('home'))

@app.route("/view_companies")
@login_required
@role_required("Applicant")
def view_companies():
    companies = Company.query.all()
    return render_template(
        "companies.html",
        companies=companies,
        title="Companies",
        layout="layout_user.html"
    )

@app.route("/company/<int:company_id>/ads")
@login_required
@role_required("Applicant")
def company_ads(company_id):
    company = Company.query.get_or_404(company_id)    
    ads = Advertisement.query\
        .filter_by(CompanyId=company_id)\
        .join(Company, Advertisement.CompanyId == Company.Id)\
        .add_columns(
            Advertisement.Id,
            Advertisement.Title,
            Advertisement.Description,
            Advertisement.Position,
            Company.Name.label('company_name')
        ).all()
    
    return render_template(
        "company_ads.html",
        company=company,
        ads=ads,
        title=f"{company.Name} - Job Listings",
        layout="layout_user.html"
    )

@app.route("/view_my_applications")
@login_required
@role_required("Applicant")
def view_my_applications():
    applications = User_Applied_Company.query\
        .join(Advertisement, User_Applied_Company.AdvertisementId == Advertisement.Id)\
        .join(Company, Advertisement.CompanyId == Company.Id)\
        .filter(User_Applied_Company.UserId == current_user.Id)\
        .add_columns(
            User_Applied_Company.Id,
            User_Applied_Company.ApplyDate,
            User_Applied_Company.CV_Path,
            Advertisement.Title,
            Advertisement.Position,
            Company.Name.label('company_name')
        )\
        .order_by(User_Applied_Company.ApplyDate.desc())\
        .all()
    
    return render_template(
        "my_applications.html",
        applications=applications,
        title="My Applications",
        layout="layout_user.html"
    )

@app.route("/view_applications/<int:ad_id>")
@login_required
@role_required("Hire")
def view_applications(ad_id):
    ad = Advertisement.query.get_or_404(ad_id)
    if ad.CompanyId != current_user.CompanyId:
        flash("You do not have permission to view these applications.", "warning")
        return redirect(url_for("home"))
    
    applications = User_Applied_Company.query\
        .join(User, User_Applied_Company.UserId == User.Id)\
        .filter(User_Applied_Company.AdvertisementId == ad_id)\
        .add_columns(
            User_Applied_Company.Id,
            User_Applied_Company.ApplyDate,
            User_Applied_Company.CV_Path,
            User.Name.label('applicant_name'),
            User.Email.label('applicant_email')
        )\
        .order_by(User_Applied_Company.ApplyDate.desc())\
        .all()
    
    return render_template(
        "view_applications.html",
        applications=applications,
        advertisement=ad,
        title="View Applications",
        layout="layout_company.html"
    )

@app.route("/download_cv/<int:application_id>")
@login_required
@role_required("Hire")
def download_cv(application_id):
    application = User_Applied_Company.query\
        .join(Advertisement)\
        .filter(User_Applied_Company.Id == application_id)\
        .first_or_404()
    
    if application.advertisement.CompanyId != current_user.CompanyId:
        flash("You do not have permission to download this CV.", "warning")
        return redirect(url_for("home"))
    
    if not os.path.exists(application.CV_Path):
        flash("CV file not found.", "danger")
        return redirect(url_for('view_applications', ad_id=application.AdvertisementId))
    
    directory = os.path.dirname(application.CV_Path)
    filename = os.path.basename(application.CV_Path)
    
    return send_from_directory(
        directory,
        filename,
        as_attachment=True
    )

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route("/test_login_status")
def test_login_status():
    return f"User Authenticated: {current_user.is_authenticated}, Session: {session.get('_user_id')}"

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return render_template("404.html"), 405

if __name__ == "__main__":
    print()
    app.run(host="0.0.0.0", port=6001)
