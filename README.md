# AbyVest AI

AbyVest is a Flask-based AI stock portfolio management application. Track holdings, view live market data, and get portfolio-aware insights from Finley (Google Gemini).

Educational use only — AI output is not professional financial advice.

## Features

- User registration, login, logout, and account updates
- Password hashing with Flask-Bcrypt
- Portfolio dashboard (invested value, current value, gain/loss)
- Buy, sell, view, and delete stock holdings
- Live quotes and company data via Finnhub (Redis-cached)
- Market ticker for selected symbols
- AI chat assistant (Gemini) with per-user chat history
- Profile image uploads via Cloudinary
- PostgreSQL + Redis via Docker Compose
- Flask-Migrate / Alembic schema migrations
- Automated unit and functional tests (external APIs mocked)

## Architecture

```text
Browser
   │
   ▼
AbyVest (Flask + Gunicorn)  :2005
   │
   ├── PostgreSQL  :5432  (internal in production)
   └── Redis       :6379  (internal in production)

External APIs: Finnhub · Google Gemini · Cloudinary
```

Production (AWS EC2 recommended for this project):

```text
Internet → Nginx :80/:443 → Gunicorn → Flask
                              ├── PostgreSQL (Docker, localhost only)
                              └── Redis (Docker, localhost only)
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.12 |
| Web | Flask, Flask-Login, Flask-WTF, Flask-Bcrypt |
| ORM / migrations | Flask-SQLAlchemy, Flask-Migrate (Alembic) |
| Cache | Redis |
| Database | PostgreSQL 15 (SQLite OK for local non-Docker) |
| APIs | Finnhub, Google Generative AI, Cloudinary |
| Server | Gunicorn |
| Containers | Docker, Docker Compose |

## Folder Structure

```text
AbyVest/
├── app.py                 # Application factory
├── wsgi.py                # Gunicorn / Flask CLI entrypoint
├── extensions.py          # db, bcrypt, login, migrate, csrf
├── models.py              # User, Stock, ChatMessage
├── services.py            # Finnhub + Redis caching
├── forms.py               # WTForms
├── routes/
│   ├── auth.py
│   ├── stocks.py
│   └── chat.py
├── templates/
├── static/
├── tests/
├── migrations/            # Alembic migrations
├── deploy/
│   ├── nginx/abyvest.conf
│   └── AWS_DEPLOYMENT.md
├── Dockerfile
├── docker-compose.yml
├── docker-compose.dev.yml
├── docker-compose.prod.yml
├── entrypoint.sh          # migrate + gunicorn
├── requirements.txt
├── .env.example
└── README.md
```

## Environment Variables

Copy `.env.example` to `.env` and fill in values. **Never commit `.env`.**

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Flask sessions / CSRF (required) |
| `FLASK_ENV` | Set `production` on deployed hosts |
| `FLASK_DEBUG` | Keep `0` in production |
| `POSTGRES_USER` | Postgres username |
| `POSTGRES_PASSWORD` | Postgres password (quote if it contains `#`) |
| `POSTGRES_DB` | Database name |
| `DATABASE_URL` | SQLAlchemy URL — use host `postgres` inside Compose |
| `REDIS_URL` | Redis URL — use host `redis` inside Compose |
| `FINNHUB_API_KEY` | Finnhub quotes/profiles |
| `GENAI_API_KEY` | Google Gemini |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary |
| `CLOUDINARY_API_KEY` | Cloudinary |
| `CLOUDINARY_API_SECRET` | Cloudinary |

Inside Docker Compose, prefer:

```env
DATABASE_URL=postgresql://postgres:YOUR_ENCODED_PASSWORD@postgres:5432/smartstocktracker
REDIS_URL=redis://redis:6379
```

URL-encode special characters in passwords (example: `#` → `%23`).

## Local Setup (Python)

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

macOS/Linux:

```bash
source venv/bin/activate
```

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create `.env` (see `.env.example`). For non-Docker local runs you can use SQLite:

```env
DATABASE_URL=sqlite:///site.db
REDIS_URL=redis://localhost:6379
```

```bash
set FLASK_APP=wsgi:app
flask db upgrade
python app.py
```

App (debug only if `FLASK_DEBUG=1`): http://127.0.0.1:5000

## Docker Setup

Prerequisites: Git, Docker Desktop.

```bash
git clone https://github.com/adithyaabhiram-28/AbyVest.git
cd AbyVest
```

Create `.env` from `.env.example`.

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
docker compose -f docker-compose.yml -f docker-compose.dev.yml ps
```

Open: http://localhost:2005

Migrations run automatically via `entrypoint.sh` on container start.

The base Compose file does **not** publish ports. The `dev` overlay publishes app `:2005` plus optional Postgres/Redis host ports for local tooling. The `prod` overlay binds the app to `127.0.0.1:2005` only and never publishes Postgres/Redis.

Stop:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml down
```

Production overlay:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Database Migrations

```bash
# Local
set FLASK_APP=wsgi:app
flask db migrate -m "Describe change"
flask db upgrade

# Inside Docker
docker compose exec app flask db upgrade
```

Do not rely on `db.create_all()` for production schema management.

## Redis

- Quote cache TTL: 60 seconds (`stock:SYMBOL`)
- Profile cache TTL: 24 hours (`profile:SYMBOL`)
- If Redis is down, the app continues and calls Finnhub directly (degraded mode)

## Tests

External APIs are mocked. No production keys required.

```bash
pytest -q
```

Inside Docker:

```bash
docker compose exec app pytest -q
```

## Production Notes

- `SECRET_KEY` is required (no insecure fallback)
- Set `FLASK_ENV=production` (enables secure cookies)
- Put Nginx in front of Gunicorn (see `deploy/nginx/abyvest.conf`)
- Do not expose ports 5432 or 6379 publicly
- Keep secrets in environment / `.env` outside the image
- Rotate any credential that was ever committed to Git history

## External Services

| Service | Used for |
|---------|----------|
| Finnhub | Quotes and company profiles |
| Google Gemini | Finley AI assistant |
| Cloudinary | Profile pictures |

## Future Improvements

- Batch Finnhub calls on the dashboard (avoid N+1 property fetches)
- Structured application logging
- Optional rate limiting on `/chat/api`
- Automated CI (GitHub Actions) for pytest + Docker build

## AWS Deployment

See [deploy/AWS_DEPLOYMENT.md](deploy/AWS_DEPLOYMENT.md) for the full EC2 + Docker + Nginx + HTTPS procedure.

**Do not deploy until you have rotated any secrets that appeared in Git history or local logs.**
