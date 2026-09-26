import pytest
from datetime import date
from unittest.mock import patch

from models import Stock
from extensions import db


class TestAuthRoutes:
    def test_home_page_loads_when_not_logged_in(self, client):
        res = client.get('/', follow_redirects=False)
        assert res.status_code == 200
        assert b'Login' in res.data

    def test_register_user(self, client, mock_external):
        res = client.post(
            '/register',
            data={
                'username': 'newguy',
                'email': 'new@guy.com',
                'password': 'securepass123',
                'confirm_password': 'securepass123',
            },
            follow_redirects=True,
        )

        assert res.status_code == 200
        assert b'Login' in res.data

        from models import User

        assert User.query.filter_by(email='new@guy.com').first() is not None

    def test_login_invalid_credentials(self, client, mock_external):
        res = client.post(
            '/login',
            data={'email': 'new@guy.com', 'password': 'wrongpassword'},
            follow_redirects=True,
        )
        assert b'Login Unsuccessful' in res.data

    def test_open_redirect_is_blocked(self, client, create_user, mock_external):
        create_user()
        res = client.post(
            '/login?next=https://evil.example/phish',
            data={'email': 'test@test.com', 'password': 'password123'},
            follow_redirects=False,
        )
        assert res.status_code in (302, 303)
        assert 'evil.example' not in res.headers.get('Location', '')


class TestDashboardAndStocks:
    def test_dashboard_loads_empty(self, logged_in_client, mock_external):
        client, user = logged_in_client
        res = client.get('/', follow_redirects=True)

        assert res.status_code == 200
        assert b'$0.00' in res.data

    def test_buy_stock_route(self, logged_in_client, mock_external):
        client, user = logged_in_client

        mock_external['finnhub'].company_profile2.return_value = {'name': 'Apple Inc'}

        res = client.post(
            '/stock/buy',
            data={
                'symbol': 'aapl',
                'shares': 5,
                'purchase_price': 150.00,
                'purchase_date': date.today().isoformat(),
            },
            follow_redirects=True,
        )

        assert res.status_code == 200
        assert b'AAPL has been added to your portfolio' in res.data
        assert Stock.query.filter_by(user_id=user.id).count() == 1

    def test_buy_rejects_zero_shares(self, logged_in_client, mock_external):
        client, user = logged_in_client
        res = client.post(
            '/stock/buy',
            data={
                'symbol': 'AAPL',
                'shares': 0,
                'purchase_price': 150.00,
                'purchase_date': date.today().isoformat(),
            },
            follow_redirects=True,
        )
        assert Stock.query.filter_by(user_id=user.id).count() == 0
        assert res.status_code == 200

    def test_delete_stock(self, logged_in_client, mock_external):
        client, user = logged_in_client

        stock = Stock(
            symbol='MSFT',
            company_name='Microsoft',
            shares=1,
            purchase_price=300.0,
            purchase_date=date.today(),
            user_id=user.id,
        )
        db.session.add(stock)
        db.session.commit()

        res = client.post(f'/stock/{stock.id}/delete', follow_redirects=True)

        assert b'has been removed from your portfolio' in res.data
        assert db.session.get(Stock, stock.id) is None

    def test_sell_partial_shares(self, logged_in_client, mock_external):
        client, user = logged_in_client

        stock = Stock(
            symbol='NVDA',
            company_name='Nvidia',
            shares=10,
            purchase_price=500.0,
            purchase_date=date.today(),
            user_id=user.id,
        )
        db.session.add(stock)
        db.session.commit()

        res = client.post(
            f'/stock/{stock.id}/sell',
            data={'shares_to_sell': 4},
            follow_redirects=True,
        )

        assert b'Successfully sold 4 shares' in res.data
        updated_stock = db.session.get(Stock, stock.id)
        assert updated_stock.shares == 6

    def test_cannot_access_another_users_stock(self, client, create_user, mock_external):
        owner = create_user(username='owner', email='owner@test.com', password='password123')
        stock = Stock(
            symbol='AAPL',
            company_name='Apple',
            shares=3,
            purchase_price=100.0,
            purchase_date=date.today(),
            user_id=owner.id,
        )
        db.session.add(stock)
        db.session.commit()
        stock_id = stock.id

        create_user(username='intruder', email='intruder@test.com', password='password123')
        client.post(
            '/login',
            data={'email': 'intruder@test.com', 'password': 'password123'},
            follow_redirects=True,
        )

        res = client.get(f'/stock/{stock_id}')
        assert res.status_code == 403

        res = client.post(f'/stock/{stock_id}/delete', follow_redirects=True)
        assert res.status_code == 403
        assert db.session.get(Stock, stock_id) is not None


class TestChatRoute:
    def test_chat_page_loads(self, logged_in_client, mock_external):
        client, user = logged_in_client
        res = client.get('/chat')
        assert res.status_code == 200

    def test_chat_api_mocked(self, logged_in_client, mock_external):
        client, user = logged_in_client

        mock_response = mock_external['gemini'].GenerativeModel.return_value
        mock_response.start_chat.return_value.send_message.return_value.text = (
            '**Test Reply** Disclaimer: This is AI-generated information, '
            'not professional financial advice.'
        )

        with patch.dict('os.environ', {'GENAI_API_KEY': 'test-key'}):
            res = client.post('/chat/api', json={'message': 'What is AAPL?'})

        assert res.status_code == 200
        assert b'Test Reply' in res.data

        from models import ChatMessage

        assert ChatMessage.query.filter_by(user_id=user.id).count() == 2
