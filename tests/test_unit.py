import pytest
from models import Stock
from unittest.mock import patch
from datetime import date

class TestStockModelUnit:
    @patch('models.get_finnhub_quote')
    def test_stock_gain_loss_calculation(self, mock_quote):
        mock_quote.return_value = {'c': 150.0}
        stock = Stock(
            symbol='AAPL',
            company_name='Apple',
            shares=10,
            purchase_price=100.0,
            purchase_date=date.today(),
            user_id=1
         )
        total_inv = stock.total_invested
        current_val = stock.current_value
        gain = stock.gain_loss
        gain_pct = stock.gain_loss_percent

        assert total_inv == 1000.0
        assert current_val == 1500.0
        assert gain == 500.0
        assert gain_pct == 50.0

    @patch('models.get_finnhub_quote')
    def test_stock_loss_calculation(self, mock_quote):
        mock_quote.return_value = {'c': 50.0}

        stock = Stock(
            symbol='TSLA',
            company_name='Tesla',
            shares=5,
            purchase_price=200.0,
            purchase_date=date.today(),
            user_id=1
        )

        assert stock.gain_loss == -750.0
        assert stock.gain_loss_percent == -75.0

    @patch('models.get_finnhub_quote')
    def test_api_callback_on_failure(self, mock_quote):
        mock_quote.return_value = None

        stock = Stock(
            symbol = 'BAD',
            company_name = 'Bad Corp',
            shares = 2,
            purchase_price = 10.0,
            purchase_date = date.today(),
            user_id = 1
        )

        assert stock.current_price == 10.0
        assert stock.current_value == 20.0