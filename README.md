# AbyVest AI

AbyVest AI is a Flask-based portfolio management app for tracking stock holdings, viewing live market movement, and getting AI-assisted portfolio insights from Finley, the built-in investment assistant.

The project is intended as an educational stock analytics application. AI responses are informational only and should not be treated as professional financial advice.

## Features

- User registration, login, logout, and account updates
- Password hashing with Flask-Bcrypt
- Portfolio dashboard with total invested value, current value, and gain/loss
- Buy, sell, view, and remove stock holdings
- Live stock quote and company data through Finnhub
- Market ticker for selected symbols
- AI chat assistant powered by Google Gemini
- Persistent chat history per user
- Profile image uploads through Cloudinary
- SQLite support for local development
- PostgreSQL-ready deployment configuration for Render

## Tech Stack

- Python 3.12
- Flask
- Flask-SQLAlchemy
- Flask-Login
- Flask-WTF
- Flask-Bcrypt
- Finnhub API
- Google Generative AI
- Cloudinary
- Gunicorn
- SQLite locally, PostgreSQL on Render

## Project Structure

```text
AbyVest/
+-- app.py                 # Main Flask application and routes
+-- forms.py               # WTForms form definitions
+-- models.py              # SQLAlchemy models
+-- requirements.txt       # Python dependencies
+-- render.yaml            # Render deployment configuration
+-- templates/             # Jinja templates
+-- static/                # CSS, logos, and profile image assets
`-- instance/              # Local SQLite database location
```

## Local Setup

1. Clone the repository and move into the project folder.

```bash
git clone <repository-url>
cd AbyVest
```

2. Create and activate a virtual environment.

```bash
python -m venv venv
```

On Windows:

```bash
venv\Scripts\activate
```

On macOS/Linux:

```bash
source venv/bin/activate
```

3. Install dependencies.

```bash
pip install -r requirements.txt
```

4. Add your `.env` file with the required API keys.
5. Start the app.

```bash
python app.py
```

The development server will start at:

```text
http://127.0.0.1:5000
```

When run with `python app.py`, the app creates the database tables automatically using `db.create_all()`.

## Usage

1. Register a new account.
2. Log in to access the dashboard.
3. Add stocks from the Buy Stock page.
4. View portfolio totals, current values, and gain/loss metrics.
5. Open the AI Assistant page to ask Finley questions about your portfolio.
6. Update account details and profile image from the Account page.

## Deployment

This project includes a `render.yaml` file for Render deployment.

Render is configured to:

- Install dependencies with `pip install -r requirements.txt`
- Start the app with `gunicorn app:app`
- Use Python `3.12.4`
- Provision a PostgreSQL database named `smart-stock-db`
- Read secrets from Render environment variables

Before deploying, add these environment variables in Render:

- `SECRET_KEY`
- `GENAI_API_KEY`
- `FINNHUB_API_KEY`
- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`
- `DATABASE_URL`

For production deployments, ensure database tables are created before serving traffic. The local `db.create_all()` block only runs when starting the app with `python app.py`, not when running through Gunicorn.

## Notes

- Do not commit `.env`, virtual environments, or local database files.
- Finnhub API limits may affect live quote availability.
- Gemini responses are saved in the database as chat history.
- Stock market and AI outputs should be used for learning and research, not as financial advice.
