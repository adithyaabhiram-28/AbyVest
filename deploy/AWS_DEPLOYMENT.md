# AbyVest — AWS Deployment Plan

Student / portfolio project. Goal: low cost, reliable for ~5–6+ months, professional demo.

**Do not start AWS provisioning until local Docker + tests pass and secrets are rotated.**

---

## Recommended architecture (Option A — start here)

```text
Internet
   │
   ▼
AWS EC2 (Ubuntu)
   ├── Nginx :80 / :443
   ├── Docker Compose
   │     ├── AbyVest (Gunicorn :2005, localhost only)
   │     ├── PostgreSQL (no public port)
   │     └── Redis (no public port)
   └── Let's Encrypt (optional domain)
```

### Cost options

| Option | What | Needed now? | Cost | Notes |
|--------|------|-------------|------|-------|
| **A. Single EC2 + Compose** | App + Postgres + Redis on one VM | **Yes — recommended** | Lowest (~one small instance) | Simple backups; fine for demo traffic |
| **B. EC2 + RDS** | Managed Postgres | No | Higher | Only if you need managed backups / multi-AZ |
| **C. EC2 + RDS + ElastiCache** | Managed Redis too | No | Highest | Overkill for this app |

**Do not add** ALB, CloudFront, Route 53, or S3 unless you later need custom domain DNS, CDN, or object storage beyond Cloudinary.

---

## Service evaluation

| Service | What it does | Need for AbyVest? | Simpler alternative |
|---------|--------------|-------------------|---------------------|
| EC2 | Virtual server | **Yes** | — |
| Nginx on EC2 | Reverse proxy / TLS | **Yes** | — |
| Docker Compose | Orchestrate app/db/redis | **Yes** | — |
| RDS | Managed Postgres | Not yet | Postgres container |
| ElastiCache | Managed Redis | Not yet | Redis container |
| ALB | Load balancer | No (single instance) | Nginx |
| CloudFront | CDN | No | — |
| Route 53 | DNS | Only if you buy a domain | Registrar DNS → EC2 IP |
| S3 | Object storage | No | Cloudinary already used |
| Elastic Beanstalk | PaaS | Optional later | EC2 + Compose is clearer for a portfolio |

---

## Security group (EC2)

| Port | Protocol | Source | Purpose |
|------|----------|--------|---------|
| 22 | TCP | Your IP only | SSH |
| 80 | TCP | 0.0.0.0/0 | HTTP |
| 443 | TCP | 0.0.0.0/0 | HTTPS |

**Never open 5432 or 6379** to the internet.

---

## Exact procedure

### 1. Prerequisites

**[LOCAL WINDOWS]**

- Working `docker compose` stack
- Passing `pytest -q`
- Fresh secrets in `.env` (rotated if ever committed/logged)
- Optional: Docker Hub account for publishing the app image

### 2. Create EC2

**[AWS CONSOLE]**

1. Region: pick one close to you
2. AMI: Ubuntu Server 22.04 or 24.04 LTS
3. Instance: `t3.small` preferred; `t3.micro` may work but is tight with Postgres+Redis+Gunicorn
4. Storage: 20–30 GB gp3
5. Security group: rules above
6. Key pair: download `.pem` / `.ppk` and store safely
7. Allocate Elastic IP and associate (stable demo URL)

### 3. SSH in

**[LOCAL WINDOWS]**

```powershell
ssh -i path\to\your-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

### 4. Install Docker + Nginx + Git

**[AWS EC2]**

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y ca-certificates curl git nginx
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
# log out and back in so docker group applies
exit
```

**[LOCAL WINDOWS]** — SSH again, then:

**[AWS EC2]**

```bash
docker --version
docker compose version
```

### 5. Clone repository

**[AWS EC2]**

```bash
cd ~
git clone https://github.com/adithyaabhiram-28/AbyVest.git
cd AbyVest
```

### 6. Environment file

**[AWS EC2]**

```bash
nano .env
```

Set all variables from `.env.example`. Use strong unique values. Inside Compose:

```env
DATABASE_URL=postgresql://postgres:ENCODED_PASSWORD@postgres:5432/smartstocktracker
REDIS_URL=redis://redis:6379
FLASK_ENV=production
FLASK_DEBUG=0
```

### 7. Start stack (no public DB/Redis)

**[AWS EC2 — PROJECT DIRECTORY]**

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose ps
docker compose logs --tail=100 app
```

Confirm migrations ran and Gunicorn is listening on `:2005` inside the container.

### 8. Nginx reverse proxy

**[AWS EC2]**

```bash
sudo cp ~/AbyVest/deploy/nginx/abyvest.conf /etc/nginx/sites-available/abyvest
sudo ln -sf /etc/nginx/sites-available/abyvest /etc/nginx/sites-enabled/abyvest
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

**[LOCAL WINDOWS]** or browser:

```text
http://YOUR_EC2_PUBLIC_IP
```

### 9. Optional domain + HTTPS

**[DOMAIN REGISTRAR]**

- Create an A record → Elastic IP

**[AWS EC2]**

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your.domain.com
```

Certbot renews via systemd timer by default.

Update `server_name` in the Nginx site if needed before Certbot.

### 10. Docker Hub (optional image workflow)

**[LOCAL WINDOWS]**

```powershell
docker login
docker build -t YOUR_DOCKERHUB_USER/abyvest:latest .
docker push YOUR_DOCKERHUB_USER/abyvest:latest
```

**[AWS EC2]** — pull instead of building, if you prefer:

Add to compose (or override) `image: YOUR_DOCKERHUB_USER/abyvest:latest` for the `app` service. **Never bake `.env` into the image.**

### 11. Health checks

**[AWS EC2]**

```bash
curl -I http://127.0.0.1
docker compose exec postgres pg_isready -U postgres
docker compose exec redis redis-cli ping
docker compose logs --tail=50 app
```

### 12. Restart behavior

Compose already uses `restart: unless-stopped`. Enable Docker on boot:

**[AWS EC2]**

```bash
sudo systemctl enable docker
```

### 13. Backups

**[AWS EC2]** — weekly dump example:

```bash
mkdir -p ~/backups
docker compose exec -T postgres pg_dump -U postgres smartstocktracker | gzip > ~/backups/abyvest-$(date +%F).sql.gz
```

Copy backups off-box periodically (another machine or encrypted object storage).

### 14. Update application

**[AWS EC2 — PROJECT DIRECTORY]**

```bash
cd ~/AbyVest
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose logs --tail=50 app
```

Migrations run on container start via `entrypoint.sh`.

### 15. Rollback

**[AWS EC2]**

```bash
git log --oneline -5
git checkout PREVIOUS_COMMIT_SHA
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Or redeploy a previous Docker Hub tag.

Restore DB only if needed:

```bash
gunzip -c ~/backups/abyvest-YYYY-MM-DD.sql.gz | docker compose exec -T postgres psql -U postgres smartstocktracker
```

### 16. Cost control

- Prefer one `t3.small` (or free-tier eligible type **if your account still qualifies** — verify in AWS Billing; do not assume)
- Use Elastic IP (free while attached)
- Stop the instance when not demoing for long stretches (data persists on EBS)
- Set a billing alarm (e.g. $15–20/month)
- Skip RDS / ElastiCache / ALB for this project phase
- Delete unused snapshots and old AMIs

---

## Checklist before going live

- [ ] All API keys and DB password rotated if ever exposed
- [ ] `.env` only on server, not in Git
- [ ] Security group: 22 (your IP), 80, 443 only
- [ ] Postgres/Redis not published publicly (`docker-compose.prod.yml`)
- [ ] Nginx fronts Gunicorn
- [ ] HTTPS if you have a domain
- [ ] `FLASK_ENV=production`, `FLASK_DEBUG=0`
- [ ] Backup script tested once
- [ ] Register / login / buy stock / chat smoke-tested on the public URL
