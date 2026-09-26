import os
from flask import Flask, render_template
from dotenv import load_dotenv
import cloudinary

from extensions import db, bcrypt, login_manager, migrate, csrf
from models import User

load_dotenv()


def _normalize_database_url(url: str) -> str:
    """Normalize DB URLs for SQLAlchemy + psycopg2-binary.

    Render and some hosts still provide postgres://. SQLAlchemy 2.1+ may
    prefer psycopg (v3) for bare postgresql://, so we pin the psycopg2 driver.
    """
    if url.startswith('postgres://'):
        url = 'postgresql://' + url[len('postgres://'):]
    if url.startswith('postgresql://') and not url.startswith('postgresql+'):
        url = 'postgresql+psycopg2://' + url[len('postgresql://'):]
    return url


def create_app(config_overrides=None):
    app = Flask(__name__)

    secret_key = os.getenv('SECRET_KEY')
    if not secret_key:
        raise RuntimeError(
            'SECRET_KEY is not set. Add it to your .env file before starting AbyVest.'
        )

    database_url = _normalize_database_url(
        os.getenv('DATABASE_URL', 'sqlite:///site.db')
    )

    is_production = os.getenv('FLASK_ENV', '').lower() == 'production'

    app.config['SECRET_KEY'] = secret_key
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = is_production
    app.config['REMEMBER_COOKIE_HTTPONLY'] = True
    app.config['REMEMBER_COOKIE_SAMESITE'] = 'Lax'
    app.config['REMEMBER_COOKIE_SECURE'] = is_production

    if config_overrides:
        app.config.update(config_overrides)

    cloudinary.config(
        cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
        api_key=os.getenv('CLOUDINARY_API_KEY'),
        api_secret=os.getenv('CLOUDINARY_API_SECRET'),
    )

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    from routes.auth import auth_bp
    from routes.stocks import stocks_bp
    from routes.chat import chat_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(stocks_bp)
    app.register_blueprint(chat_bp)

    @app.errorhandler(404)
    def error_404(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def error_500(e):
        return render_template('500.html'), 500

    return app


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


if __name__ == '__main__':
    application = create_app()
    debug = os.getenv('FLASK_DEBUG', '0') == '1'
    application.run(debug=debug)
