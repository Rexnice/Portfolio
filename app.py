# app.py

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateField, FileField, SubmitField, BooleanField
from wtforms.validators import DataRequired
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
import os
from dotenv import load_dotenv
from datetime import datetime
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') 

 # Update with PostgreSQL credentials
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['CV_UPLOAD_FOLDER'] = 'static/cvs'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}



# Email configuration – use Gmail + App Password
app.config['MAIL_SERVER']      = 'smtp.gmail.com'
app.config['MAIL_PORT']        = 587
app.config['MAIL_USE_TLS']     = True
app.config['MAIL_USE_SSL']     = False
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

mail = Mail(app)

db = SQLAlchemy(app)



@app.context_processor
def inject_now():
    return dict(now=datetime.now)

# Helper function for allowed files
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Models
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(200), nullable=False)
    date = db.Column(db.Date, nullable=False)
    featured = db.Column(db.Boolean, default=False)
    github_link = db.Column(db.String(500), nullable=True)

class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

class Tool(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_filename = db.Column(db.String(200), nullable=True)
    
class CV(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)         # stored filename (secure)
    original_name = db.Column(db.String(200), nullable=False)    # original uploaded name
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

# Forms
class ProjectForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    image = FileField('Image', validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()])
    featured = BooleanField('Featured')
    submit = SubmitField('Submit')
    github_link = StringField('GitHub Repository URL (optional)', validators=[])

class BlogPostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    content = TextAreaField('Content', validators=[DataRequired()])
    submit = SubmitField('Submit')

class ToolForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    submit = SubmitField('Submit')
    image = FileField('Tool Logo (optional)')

# Routes for main pages
@app.route('/', methods=['GET', 'POST'])
def index():
    featured_project = Project.query.filter_by(featured=True).first()
    projects = Project.query.filter_by(featured=False).all()

    if request.method == 'POST':
        name    = request.form.get('name')
        email   = request.form.get('email')
        message = request.form.get('message')

        if name and email and message:
            try:
                msg = Message(
                    subject=f"New message from {name} via Portfolio",
                    recipients=['ekerekeernest10@gmail.com'],           # ← where YOU receive it
                    body=f"From: {name}\nEmail: {email}\n\nMessage:\n{message}",
                    reply_to=email
                )
                mail.send(msg)
                flash('Message sent successfully! Thank you.', 'success')
            except Exception as e:
                flash(f'Error sending message: {str(e)}', 'error')
        else:
            flash('Please fill all fields.', 'error')

        return redirect(url_for('index'))  # or render_template again if you prefer

    return render_template(
        'index.html',
        featured_project=featured_project,
        projects=projects,
        active_page='projects',
        is_index=True
    )

@app.route('/tools')
def tools():
    tools = Tool.query.all()
    return render_template('generic.html', tools=tools, active_page='tools')

@app.route('/blog')
def blog():
    posts = BlogPost.query.order_by(BlogPost.date.desc()).all()
    return render_template('elements.html', posts=posts, active_page='blog')

# Admin routes for projects
@app.route('/admin/project/new', methods=['GET', 'POST'])
def new_project():
    form = ProjectForm()
    if form.validate_on_submit():
        if form.image.data:
            file = form.image.data
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                project = Project(
                    title=form.title.data,
                    description=form.description.data,
                    image=filename,
                    date=form.date.data,
                    featured=form.featured.data,
                    github_link=form.github_link.data.strip() or None
                )
                db.session.add(project)
                db.session.commit()
                flash('Project added successfully!')
                return redirect(url_for('index'))
    return render_template('admin_form.html', form=form, title='New Project')

@app.route('/admin/project/<int:id>/delete', methods=['POST'])
def delete_project(id):
    project = Project.query.get_or_404(id)
    if project.image:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], project.image))
    db.session.delete(project)
    db.session.commit()
    flash('Project deleted successfully!')
    return redirect(url_for('index'))

# Admin routes for blog posts
@app.route('/admin/blog/new', methods=['GET', 'POST'])
def new_blog():
    form = BlogPostForm()
    if form.validate_on_submit():
        post = BlogPost(title=form.title.data, content=form.content.data)
        db.session.add(post)
        db.session.commit()
        flash('Blog post added successfully!')
        return redirect(url_for('blog'))
    return render_template('admin_form.html', form=form, title='New Blog Post')

@app.route('/admin/blog/<int:id>/delete', methods=['POST'])
def delete_blog(id):
    post = BlogPost.query.get_or_404(id)
    db.session.delete(post)
    db.session.commit()
    flash('Blog post deleted successfully!')
    return redirect(url_for('blog'))

# Admin routes for tools
@app.route('/admin/tool/new', methods=['GET', 'POST'])
def new_tool():
    form = ToolForm()
    if form.validate_on_submit():
        filename = None
        if form.image.data and allowed_file(form.image.data.filename):
            filename = secure_filename(form.image.data.filename)
            form.image.data.save(os.path.join('static/tools', filename))

        tool = Tool(
            name=form.name.data,
            description=form.description.data,
            image_filename=filename
        )
        db.session.add(tool)
        db.session.commit()
        flash('Tool added successfully!')
        return redirect(url_for('tools'))
    return render_template('admin_form.html', form=form, title='New Tool')

@app.route('/admin/tool/<int:id>/delete', methods=['POST'])
def delete_tool(id):
    tool = Tool.query.get_or_404(id)
    db.session.delete(tool)
    db.session.commit()
    flash('Tool deleted successfully!')
    return redirect(url_for('tools'))

# Public CV page — shows latest CV (only one active at a time)
@app.route('/cv')
def cv():
    latest_cv = CV.query.order_by(CV.upload_date.desc()).first()
    return render_template('cv.html', cv=latest_cv, active_page='cv')

# Admin: Upload new CV (replaces previous one automatically)
@app.route('/admin/cv/upload', methods=['GET', 'POST'])
def upload_cv():
    if request.method == 'POST':
        if 'cv_file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)

        file = request.files['cv_file']
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)

        if file and file.filename.lower().endswith('.pdf'):
            # Delete old CV file and record if exists
            old_cv = CV.query.first()
            if old_cv:
                old_path = os.path.join(app.config['CV_UPLOAD_FOLDER'], old_cv.filename)
                if os.path.exists(old_path):
                    os.remove(old_path)
                db.session.delete(old_cv)

            # Save new CV
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['CV_UPLOAD_FOLDER'], filename)
            file.save(save_path)

            new_cv = CV(
                filename=filename,
                original_name=file.filename
            )
            db.session.add(new_cv)
            db.session.commit()

            flash('CV uploaded successfully!', 'success')
            return redirect(url_for('cv'))
        else:
            flash('Only PDF files are allowed.', 'error')

    return render_template('admin_cv_upload.html')


# Optional: Delete current CV
@app.route('/admin/cv/delete', methods=['POST'])
def delete_cv():
    cv_record = CV.query.first()
    if cv_record:
        file_path = os.path.join(app.config['CV_UPLOAD_FOLDER'], cv_record.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        db.session.delete(cv_record)
        db.session.commit()
        flash('CV deleted successfully.', 'success')
    else:
        flash('No CV to delete.', 'info')
    return redirect(url_for('cv'))


# if __name__ == '__main__':
#     with app.app_context():
#         db.create_all()
#     app.run(debug=True)

application = app