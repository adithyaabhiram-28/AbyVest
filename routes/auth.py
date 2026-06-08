from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from extensions import db, bcrypt
from models import User
from forms import RegistrationForm, LoginForm, UpdateForm
import cloudinary.uploader

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def home():
    if current_user.is_authenticated:
        from models import Stock
        stocks = Stock.query.filter_by(user_id=current_user.id).all()
        total_invested = sum(stock.total_invested for stock in stocks)
        current_value = sum(stock.current_value for stock in stocks)
        gain_loss = current_value - total_invested
        gain_loss_percent = (gain_loss / total_invested) * 100 if total_invested > 0 else 0
        return render_template('dashboard.html', stocks=stocks, total_invested=total_invested, current_value=current_value, gain_loss=gain_loss, gain_loss_percent=gain_loss_percent)
    return render_template('home.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('auth.home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register.html', title='Register', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('Login Successful', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('auth.home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.home'))

@auth_bp.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateForm()
    if form.validate_on_submit():
        if form.picture.data:
            upload_result = cloudinary.uploader.upload(form.picture.data, folder='static/profile_pics')
            current_user.image_file = upload_result['secure_url']
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('auth.account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    return render_template('account.html', title='Account', image_file=current_user.image_file, form=form)

@auth_bp.route('/about')
def about():
    return render_template('about.html', title='About')