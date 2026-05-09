from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone
import os
import finnhub

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    image_file = db.Column(db.String(500), nullable=False, default='https://res.cloudinary.com/ds74jszcl/image/upload/c_fill,g_face,w_300,h_300/v1777964984/default_vlnm6j.jpg')

    stocks = db.relationship('Stock', backref='owner', lazy=True)
    messages = db.relationship('ChatMessage', backref='author', lazy=True)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"
    
class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    shares = db.Column(db.Integer, nullable=False)
    purchase_price = db.Column(db.Float, nullable=False)
    purchase_date = db.Column(db.Date, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    @property
    def current_price(self):
        try:
            finnhub_client = finnhub.Client(api_key=os.getenv('FINNHUB_API_KEY'))
            quote = finnhub_client.quote(symbol=self.symbol)
            return quote.get('c', self.purchase_price)
        except:
            return self.purchase_price
        
    @property
    def total_invested(self):
        return self.shares * self.purchase_price
    
    @property
    def current_value(self):
        return self.shares * self.current_price
    
    @property
    def gain_loss(self):
        return self.current_value - self.total_invested
    
    @property
    def gain_loss_percent(self):
        if self.total_invested == 0:
            return 0
        return (self.gain_loss / self.total_invested) * 100

    def __repr__(self):
        return f"Stock('{self.symbol}', {self.shares} shares)"
    
class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))