import pytest
from app import create_app
from extensions import db
from models import User, Stock, ChatMessage
from unittest.mock import patch

@pytest.fixture(scope='function')
def client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()

@pytest.fixture(scope='function')
def mock_external():
    with patch('services.redis_client') as mock_redis, \
    patch('services.finnhub_client') as mock_finnhub, \
    patch('routes.chat.genai') as mock_gemini, \
    patch('routes.auth.cloudinary') as mock_cloudinary:
        mock_redis.get.return_value = None
        mock_redis.setex.return_value = True

        yield {
            'redis' : mock_redis,
            'finnhub' : mock_finnhub,
            'gemini' : mock_gemini,
            'cloudinary' : mock_cloudinary
        }

@pytest.fixture
def create_user(client):
    def _create_user(username='testuser', email='test@test.com', password='password123'):
        user = User(username=username, email=email, password=password)
        client.post('/register', data = dict(
            username=username, email=email, password=password, confirm_password=password
        ), follow_redirects=True)
        return User.query.filter_by(email=email).first()
    return _create_user

@pytest.fixture
def logged_in_client(client, create_user, mock_external):
    user = create_user()
    client.post('/login', data = dict(email='test@test.com', password='password123'), follow_redirects=True)
    return client, user