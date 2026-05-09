from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, FloatField, DateField, FileField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from flask_wtf.file import FileAllowed
from models import User

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username is already taken. Please choose a different one.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email is already in use.')
        
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    submit = SubmitField('Login')

class StockForm(FlaskForm):
    symbol = StringField('Stock Symbol', validators=[DataRequired()])
    shares = IntegerField('Number of Shares', validators=[DataRequired()])
    purchase_price = FloatField('Purchase Price per Share ($)', validators=[DataRequired()])
    purchase_date = DateField('Purchase Date', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Buy Stock')

class UpdateForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    picture = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'png','webp'])])
    submit = SubmitField('Update')

    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('Username is already taken. Please choose a different one.')
    
    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('Email is already in use.')
            
class SellStockForm(FlaskForm):
    shares_to_sell = IntegerField('Number of Shares to Sell', validators=[DataRequired()])
    submit = SubmitField('Sell Stock')