print("1. Starting app file")

import os
from flask import Flask, render_template, redirect, url_for, flash, abort, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, login_user, login_required
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
from models import db, User, Stock, ChatMessage
from forms import RegistrationForm, LoginForm, StockForm, UpdateForm, SellStockForm
import finnhub
import google.generativeai as genai
import markdown
import cloudinary
import cloudinary.uploader

print("2. Imports completed")

load_dotenv()

finnhub_client = finnhub.Client(api_key=os.getenv('FINNHUB_API_KEY'))

print("3. dotenv loaded")

app = Flask(__name__)

print("4. Flask app created")

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

print("5. DB config set")

db.init_app(app)
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

print("6. DB initialized")

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route('/')
def home():
    if current_user.is_authenticated:
        stocks = Stock.query.filter_by(user_id=current_user.id).all()

        total_invested = sum(stock.total_invested for stock in stocks)
        current_value = sum(stock.current_value for stock in stocks)
        gain_loss = current_value - total_invested
        gain_loss_percent = (gain_loss / total_invested * 100) if total_invested > 0 else 0

        return render_template('dashboard.html', stocks=stocks, total_invested=total_invested, current_value=current_value, gain_loss=gain_loss, gain_loss_percent=gain_loss_percent)
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Account is created! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Login unsuccessful. Please check email and password.', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateForm()
    if form.validate_on_submit():
        if form.picture.data:
            upload_result = cloudinary.uploader.upload(form.picture.data, folder="profile_pics")
            current_user.image_file = upload_result['secure_url']
        
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = current_user.image_file
    return render_template('account.html', title='Account', image_file=image_file, form=form)

@app.route('/about')
def about():
    return render_template('about.html', title='About')

@app.route('/logout')
def logout():
    from flask_login import logout_user
    logout_user()
    return redirect(url_for('home'))

@app.route('/stock/buy', methods=['GET', 'POST'])
@login_required
def buy_stock():
    form = StockForm()
    if form.validate_on_submit():
        symbol = form.symbol.data.upper().strip()
        try:
            profile = finnhub_client.company_profile2(symbol=symbol)
            company_name = profile.get("name", symbol)
        except:
            company_name = symbol

        stock = Stock(symbol=symbol, company_name=company_name, shares=form.shares.data, purchase_price=form.purchase_price.data, purchase_date=form.purchase_date.data, user_id=current_user.id)
        db.session.add(stock)
        db.session.commit()
        flash(f'{symbol} has been added to your portfolio!', 'success')
        return redirect(url_for('home'))
    return render_template('buy_stock.html', title='Buy Stock', form=form)

@app.route('/stock/<int:stock_id>/delete', methods=['POST'])
@login_required
def delete_stock(stock_id):
    stock = Stock.query.get_or_404(stock_id)
    if stock.owner != current_user:
        abort(403)
    db.session.delete(stock)
    db.session.commit()
    flash(f'{stock.symbol} has been removed from your portfolio.', 'info')
    return redirect(url_for('home'))

@app.route('/stock/<int:stock_id>/sell', methods=['POST'])
@login_required
def  sell_stock(stock_id):
    stock = Stock.query.get_or_404(stock_id)
    if stock.owner != current_user:
        abort(403)
    form = SellStockForm()
    if form.validate_on_submit():
        shares_to_sell = form.shares_to_sell.data
        if shares_to_sell <= 0:
            flash('You must sell at least 1 share.', 'danger')
        elif shares_to_sell > stock.shares:
            flash(f'You only own {stock.shares} shares of {stock.symbol}.', 'danger')
        else:
            if shares_to_sell < stock.shares:
                stock.shares -= shares_to_sell
                db.session.commit()
                flash(f'Successfully sold {shares_to_sell} shares of {stock.symbol}. {stock.shares} shares remaining.', 'success')
                return redirect(url_for('stock_detail', stock_id=stock_id))
            else:
                symbol = stock.symbol
                db.session.delete(stock)
                db.session.commit()
                flash(f'Successfully sold all shares of {symbol}.', 'success')
                return redirect(url_for('home'))
    return redirect(url_for('stock_detail', stock_id=stock_id))

@app.route('/stock/<int:stock_id>')
@login_required
def stock_detail(stock_id):
    stock = Stock.query.get_or_404(stock_id)
    if stock.owner != current_user:
        abort(403)
    company_info = {}
    try:
        profile = finnhub_client.company_profile2(symbol=stock.symbol)
        quote = finnhub_client.quote(symbol=stock.symbol)
        company_info['sector'] = profile.get('finnhubIndustry', 'N/A')
        company_info['industry'] = profile.get('finnhubIndustry', 'N/A')
        company_info['market_cap'] = profile.get('marketCapitalization', 'N/A')
        company_info['fifty_two_week_high'] = quote.get('h', 'N/A')
        company_info['fifty_two_week_low'] = quote.get('l', 'N/A')
        company_info['description'] = profile.get('name', 'No description available.')
    except:
        company_info['sector'] = 'N/A'
        company_info['industry'] = 'N/A'
        company_info['fifty_two_week_high'] = 'N/A'
        company_info['fifty_two_week_low'] = 'N/A'
        company_info['description'] = 'Could not load data.'
    form = SellStockForm()
    return render_template('stock_detail.html', title=stock.symbol, stock=stock, info=company_info, form=form)

@app.route('/market-data')
@login_required
def market_data():
    symbols = ['SPY','NVDA','TSLA', 'AAPL', 'MSFT']
    market = []

    for symbol in symbols:
        try:
            quote = finnhub_client.quote(symbol=symbol)
            current_price = quote.get('c', 'N/A')
            previous_close = quote.get('pc', 'N/A')

            change_percent = 0

            if previous_close:
                change_percent = (
                    (current_price - previous_close)/previous_close
                )*100

            market.append({
                'symbol' : symbol,
                'change' : round(change_percent, 2)
            })
        except:
            market.append({
                'symbol' : symbol,
                'change' : 0
            })
    return jsonify(market)

@app.route('/chat')
@login_required
def chat():
    chat_history = ChatMessage.query.filter_by(user_id=current_user.id).order_by(ChatMessage.timestamp.asc()).all()
    return render_template('chat.html', title='Chat', chat_history=chat_history)

@app.route('/chat/api', methods=['POST'])
@login_required
def chat_api():
    data = request.get_json()
    user_message = data.get('message', '')

    # Get the actual logged-in user's ID
    user_id = current_user.id  

    stocks = Stock.query.filter_by(user_id=user_id).all()
    portfolio_context = "User's Portfolio:\n"
    total_invested = 0
    current_value = 0 

    if not stocks:
        portfolio_context += "The user currently has no stocks in their portfolio.\n"
    else:
        for stock in stocks:
            portfolio_context += f"- {stock.symbol} ({stock.company_name}): {stock.shares} shares. Buy Price: ${stock.purchase_price:.2f}. Current Price: ${stock.current_price:.2f}. Gain/Loss: {stock.gain_loss_percent:.2f}%.\n"
            total_invested += stock.total_invested
            current_value += stock.current_value
        portfolio_context += f"\nTotal Invested: ${total_invested:.2f}. Current Value: ${current_value:.2f}.\n"

    system_prompt = f"""You are Finley, an expert AI investment assistant integrated into an AbyVest AI application. You have a professional, analytical, yet friendly tone.

{portfolio_context}

Your responsibilities:
- Analyze the user's personal portfolio above and give tailored advice.
- Suggest BUY, SELL, or HOLD decisions based on current market conditions and their specific stats.
- Recommend how many shares to buy using position-sizing logic if they ask.
- Warn about overexposed or high-risk positions based on their holdings.
- Answer general stock market questions clearly.
- Always use proper formatting:
    * Headings
    * Bullet points
    * Numbered lists
    * Short paragraphs
    * Bold important stock names
- Keep responses visually organized and professional.
- IMPORTANT: Always end your response with a disclaimer: *"Disclaimer: This is AI-generated information, not professional financial advice."* """

    db_message = ChatMessage.query.filter_by(user_id=user_id).order_by(ChatMessage.timestamp.desc()).limit(20).all()
    db_message.reverse()

    gemini_history = []
    for msg in db_message:
        role = "user" if msg.role == "user" else "model"
        gemini_history.append({"role": role, "parts": [msg.content]})

    try:
        genai.configure(api_key=os.getenv('GENAI_API_KEY'))  # ✅ FIXED

        model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            system_instruction=system_prompt
        )
        
        chat_session = model.start_chat(history=gemini_history)
        response = chat_session.send_message(user_message)
        formatted_reply = markdown.markdown(response.text)
        ai_reply = formatted_reply
    except Exception as e:
        ai_reply = f"Sorry, I encountered an error: {str(e)}"

    user_msg_record = ChatMessage(user_id=user_id, role='user', content=user_message)
    db.session.add(user_msg_record)

    ai_msg_record = ChatMessage(user_id=user_id, role='assistant', content=ai_reply)
    db.session.add(ai_msg_record)

    db.session.commit()

    return jsonify({'reply': ai_reply})

@app.route('/chat/clear', methods=['POST'])
@login_required
def clear_chat():
    ChatMessage.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return jsonify({'status': 'cleared'})

@app.errorhandler(404)
def error_404(error):
    return render_template('404.html', title='404'), 404

@app.errorhandler(500)
def error_500(error):
    return render_template('500.html', title='500'), 500

if __name__ == '__main__':
    with app.app_context():
        print("7. Before create_all")
        db.create_all()
        print("8. After create_all")
    print("9. Starting Flask server")
    app.run(debug=True)
