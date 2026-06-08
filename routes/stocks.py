from flask import Blueprint, render_template, redirect, url_for, flash, abort, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import Stock
from forms import StockForm, SellStockForm
from services import get_finnhub_quote, get_finnhub_profile

stocks_bp = Blueprint('stocks', __name__)

@stocks_bp.route('/stock/buy', methods=['GET', 'POST'])
@login_required
def buy_stock():
    form = StockForm()
    if form.validate_on_submit():
        symbol = form.symbol.data.upper().strip()
        profile = get_finnhub_profile(symbol)
        company_name = profile.get('name', symbol) if profile else symbol

        stock = Stock(symbol=symbol, company_name=company_name, shares=form.shares.data, purchase_price=form.purchase_price.data, purchase_date=form.purchase_date.data, user_id=current_user.id)
        db.session.add(stock)
        db.session.commit()
        flash(f'{symbol} has been added to your portfolio!', 'success')
        return redirect(url_for('auth.home'))
    return render_template('buy_stock.html', title='Buy Stock', form=form)

@stocks_bp.route('/stock/<int:stock_id>/delete', methods=['POST'])
@login_required
def delete_stock(stock_id):
    stock = Stock.query.get_or_404(stock_id)
    if stock.owner != current_user:
        abort(403)
    db.session.delete(stock)
    db.session.commit()
    flash(f'{stock.symbol} has been removed from your portfolio.', 'info')
    return redirect(url_for('auth.home'))

@stocks_bp.route('/stock/<int:stock_id>/sell', methods=['POST'])
@login_required
def sell_stock(stock_id):
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
                return redirect(url_for('stocks.stock_detail', stock_id=stock.id))
            else:
                symbol = stock.symbol
                db.session.delete(stock)
                db.session.commit()
                flash(f'Successfully sold all shares of {symbol}.', 'success')
                return redirect(url_for('auth.home'))   
    return redirect(url_for('stocks.stock_detail', stock_id=stock.id))

@stocks_bp.route('/stock/<int:stock_id>')
@login_required
def stock_detail(stock_id):
    stock = Stock.query.get_or_404(stock_id)
    if stock.owner != current_user:
        abort(403)
    company_info = {}
    profile = get_finnhub_profile(stock.symbol)
    quote = get_finnhub_quote(stock.symbol)

    company_info = {
        'sector': profile.get('finnhubIndustry', 'N/A') if profile else 'N/A',
        'market_cap': profile.get('marketCapitalization', 'N/A') if profile else 'N/A',
        'description': profile.get('name', 'No description.') if profile else 'Could not load.',
        'fifty_two_week_high': quote.get('h', 'N/A') if quote else 'N/A',
        'fifty_two_week_low': quote.get('l', 'N/A') if quote else 'N/A',
    }

    form = SellStockForm()
    return render_template('stock_detail.html', title=stock.symbol, stock=stock, info=company_info, form=form)

@stocks_bp.route('/market-data')
@login_required
def market_data():
    symbols = ['SPY', 'NVDA', 'TSLA', 'AAPL', 'MSFT']
    market = []
    for symbol in symbols:
        quote = get_finnhub_quote(symbol)
        if quote:
            current_price = quote.get('c', 'N/A')
            previous_close = quote.get('pc', 'N/A')
            change_percent = ((current_price - previous_close) / previous_close * 100) if previous_close else 0
            market.append({
                'symbol' : symbol,
                'change' : round(change_percent, 2)
            })
        else:
            market.append({
                'symbol' : symbol,
                'change' : 0
            })
    return jsonify(market)