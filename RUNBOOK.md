# Track4U — Operations Runbook

Everything you need to install, configure, run, and maintain this project — in copy-paste commands.

---

## 1. First-Time Setup (Run Once)

```bash
# Clone into your directory
cd /home/rk/Documents/Projects/track4U-1/task-manager

# Create and activate Python virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows PowerShell

# Install all dependencies
pip install -r requirements.txt

# Verify key packages installed
pip show fastapi apscheduler aiosmtplib python-whois
```

---

## 2. Generate Secrets (Run Once Before Going Live)

```bash
# Generate JWT_SECRET — paste the output into .env
python -c "import secrets; print('JWT_SECRET=' + secrets.token_hex(32))"

# Generate INTERNAL_API_TOKEN — paste the output into .env
python -c "import secrets; print('INTERNAL_API_TOKEN=' + secrets.token_hex(32))"
```

---

## 3. Configure .env

```bash
# Open and edit your environment file
nano .env      # or: code .env  / vim .env

# Minimum required fields to fill in:
#   SMTP_USER         → your Gmail address
#   SMTP_PASSWORD     → 16-char Gmail App Password (NOT your login password)
#   ALERT_FROM_EMAIL  → same as SMTP_USER
#   ALERT_TO_EMAILS   → email(s) to always receive alerts
#   JWT_SECRET        → generated in step 2
#   INTERNAL_API_TOKEN → generated in step 2
```

**Gmail App Password:**
```
1. Go to: https://myaccount.google.com/security
2. Enable 2-Step Verification (required)
3. Go to: https://myaccount.google.com/apppasswords
4. App: Mail | Device: Other → type "Track4U"
5. Copy the 16-character password shown
```

**Test your SMTP credentials:**
```bash
python -c "
import smtplib
host, port = 'smtp.gmail.com', 587
user = input('Gmail: ')
pw = input('App password: ')
s = smtplib.SMTP(host, port)
s.starttls()
s.login(user, pw)
print('✅ SMTP connection OK')
s.quit()
"
```

---

## 4. Database Setup (Run After Every Pull)

```bash
# Apply all pending migrations (creates tables on first run)
alembic upgrade head

# Verify migration state
alembic current

# View full migration history
alembic history --verbose

# Roll back one migration (if something goes wrong)
alembic downgrade -1

# Roll back ALL migrations (wipe schema, keep file)
alembic downgrade base

# Completely reset the database (destructive!)
rm -f data/app.db && alembic upgrade head
```

---

## 5. Start the Server

**Development (with auto-reload on file changes):**
```bash
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Development on a different port:**
```bash
uvicorn app.main:app --reload --port 8001
```

**Production (with Gunicorn + 1 worker):**
```bash
# Use 1 worker to avoid duplicate scheduled jobs
source .venv/bin/activate
gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  -w 1 \
  -b 0.0.0.0:8000 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
```

**Run in background with nohup:**
```bash
nohup gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  -w 1 -b 0.0.0.0:8000 \
  > logs/server.log 2>&1 &
echo $! > server.pid
echo "Server PID: $(cat server.pid)"

# Stop the background server
kill $(cat server.pid)
```

---

## 6. Verify the Server is Running

```bash
# Basic health check
curl http://localhost:8000/health

# Expected output:
# {
#   "status": "healthy",
#   "version": "2.0.0",
#   "environment": "development",
#   "scheduler": "running (2× daily: 8AM + 8PM IST)",
#   "smtp_configured": true
# }

# Open in browser
xdg-open http://localhost:8000           # Linux
# open http://localhost:8000             # macOS
# start http://localhost:8000            # Windows

# View interactive API docs
xdg-open http://localhost:8000/docs
```

---

## 7. Email Alert Testing

**Test website expiry checks (sends emails if configured):**
```bash
curl -X POST http://localhost:8000/api/v1/internal/run-expiry-checks \
  -H "X-Internal-Token: $(grep INTERNAL_API_TOKEN .env | cut -d= -f2)"
```

**Test reminder checks:**
```bash
curl -X POST http://localhost:8000/api/v1/internal/run-reminder-checks \
  -H "X-Internal-Token: $(grep INTERNAL_API_TOKEN .env | cut -d= -f2)"
```

**Test task due-date alerts:**
```bash
curl -X POST http://localhost:8000/api/v1/internal/run-task-alerts \
  -H "X-Internal-Token: $(grep INTERNAL_API_TOKEN .env | cut -d= -f2)"
```

**Test email (via Settings page or curl):**
```bash
# Via Settings → Test Email button in the UI (Settings page)
# Or via curl:
curl -X POST http://localhost:8000/api/v1/internal/send-test-email \
  -H "X-Internal-Token: $(grep INTERNAL_API_TOKEN .env | cut -d= -f2)" \
  -H "Content-Type: application/json" \
  -d '{"to_email": "you@gmail.com"}'
```

**Run both at once (same as scheduler does):**
```bash
curl -X POST http://localhost:8000/api/v1/internal/run-all-checks \
  -H "X-Internal-Token: $(grep INTERNAL_API_TOKEN .env | cut -d= -f2)"
```

**Expected log output when emails fire:**
```
📧 Domain alert → admin@yourcompany.com (12d left)
📧 SSL alert → admin@yourcompany.com (8d left)
📧 Reminder alert sent: 'Gmail Password Expiry' → admin@yourcompany.com
```

**If SMTP is not configured (stub mode):**
```
[STUB EMAIL — configure SMTP_USER in .env to send real mail]
  To     : admin@yourcompany.com
  Subject: [Track4U] Domain Expiry: example.com — 12 days left
```

---

## 8. User & API Management

**Sign up a new user via API:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Admin User",
    "email": "admin@yourcompany.com",
    "password": "SecurePass123!",
    "org_name": "My Company"
  }'
```

**Log in and get a token:**
```bash
curl -c cookies.txt -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@yourcompany.com", "password": "SecurePass123!"}'
```

**Add a website to track:**
```bash
curl -b cookies.txt -X POST http://localhost:8000/api/v1/websites \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "label": "Main Site"}'
```

**Create a custom reminder:**
```bash
curl -b cookies.txt -X POST http://localhost:8000/api/v1/reminders \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Gmail Password Expiry",
    "description": "Reset at myaccount.google.com",
    "target_date": "2026-11-30",
    "remind_days_before": 25
  }'
```

---

## 9. Process & Log Management

**Check if server is running:**
```bash
ps aux | grep uvicorn
# or
ps aux | grep gunicorn
```

**View live logs (if running with nohup):**
```bash
tail -f logs/server.log
```

**Check what's on port 8000:**
```bash
ss -tlnp | grep 8000
# or
lsof -i :8000
```

**Kill any process on port 8000:**
```bash
kill $(lsof -t -i:8000)
```

---

## 10. Update & Maintenance

**Pull latest code and restart:**
```bash
git pull
source .venv/bin/activate
pip install -r requirements.txt    # in case dependencies changed
alembic upgrade head               # in case new migrations were added
# Restart your server
```

**Database inspection (SQLite — local dev):**
```bash
# Open SQLite shell
sqlite3 data/app.db

# Useful queries inside sqlite3:
.tables                            -- list all tables
.schema tracked_websites           -- show table structure
SELECT * FROM users;               -- view all users
SELECT url, domain_expiry_date, ssl_expiry_date FROM tracked_websites;
SELECT * FROM custom_reminders;
SELECT * FROM expiry_alert_logs ORDER BY sent_at DESC LIMIT 20;
.quit
```

**Database inspection (SQLite — Docker):**
```bash
# Open SQLite shell inside the running container
docker exec -it track4u_api sqlite3 /app/data/app.db
```

---

## 10a. Data Backup & Restore (Docker)

The database lives in a Docker **named volume** (`task-manager_sqlite_data`).
This volume persists across container rebuilds and `docker compose down / up` cycles.

### Quick one-liner backup (copy from volume → host)
```bash
# Copies app.db from inside the container to ./data/ on your host
docker cp track4u_api:/app/data/app.db ./data/app_$(date +%Y%m%d_%H%M%S).db
```

### Use the backup script
```bash
# Make it executable (first time only)
chmod +x scripts/backup-db.sh

# Backup (timestamped + updates latest.db)
./scripts/backup-db.sh backup

# List available backups
./scripts/backup-db.sh list

# Restore from latest backup (confirms before overwriting)
./scripts/backup-db.sh restore

# Restore from a specific backup file
./scripts/backup-db.sh restore ./data/app_20260811_120000.db
```

### Zero-data-loss redeployment (git pull → docker rebuild)
```bash
# 1. Backup first (always!)
./scripts/backup-db.sh backup

# 2. Pull new code
git pull

# 3. Rebuild and restart — named volume is preserved automatically
docker compose up -d --build

# 4. Verify app is running with your data intact
curl http://localhost:8000/health
```

> **Why is data safe across rebuilds?**
> The SQLite database is stored in a Docker named volume (`task-manager_sqlite_data`),
> not inside the container image. Rebuilding the image does **not** delete the volume.
> Only `docker compose down -v` or `docker volume rm` would delete it.

### Migrate to a new server
```bash
# On OLD server:
./scripts/backup-db.sh backup
scp ./data/latest.db newserver:/opt/track4u/data/latest.db

# On NEW server:
docker compose up -d --build   # start fresh container
./scripts/backup-db.sh restore /opt/track4u/data/latest.db
```

---

## 11. systemd Service (Auto-start on Boot)

Create `/etc/systemd/system/track4u.service`:
```ini
[Unit]
Description=Track4U SaaS Server
After=network.target

[Service]
User=rk
WorkingDirectory=/home/rk/Documents/Projects/track4U-1/task-manager
Environment="PATH=/home/rk/Documents/Projects/track4U-1/task-manager/.venv/bin"
ExecStart=/home/rk/Documents/Projects/track4U-1/task-manager/.venv/bin/gunicorn \
    app.main:app \
    -k uvicorn.workers.UvicornWorker \
    -w 1 \
    -b 0.0.0.0:8000 \
    --timeout 120
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable track4u
sudo systemctl start track4u

# Check status
sudo systemctl status track4u

# View logs
sudo journalctl -u track4u -f

# Restart after updates
sudo systemctl restart track4u
```

---

## 12. Environment Variable Quick Reference

| Variable | Example Value | How to Generate |
|----------|--------------|-----------------|
| `JWT_SECRET` | `a3f...9d` | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `INTERNAL_API_TOKEN` | `b7c...4e` | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `SMTP_USER` | `you@gmail.com` | Your Gmail address |
| `SMTP_PASSWORD` | `abcdefghijklmnop` | Gmail App Password (16 chars, no spaces) |
| `ALERT_FROM_EMAIL` | `you@gmail.com` | Same as SMTP_USER usually |
| `ALERT_TO_EMAILS` | `a@b.com,c@d.com` | Comma-separated, manual |
| `ALERT_THRESHOLD_DAYS` | `30` | How many days before expiry to alert |
| `EMAIL_ALERT_DEDUP_HOURS` | `11` | Min hours between repeat alerts |
| `SCHEDULER_HOUR_1` | `2` | UTC hour of first daily run |
| `SCHEDULER_MINUTE_1` | `30` | UTC minute of first daily run |
| `SCHEDULER_HOUR_2` | `14` | UTC hour of second daily run |
| `SCHEDULER_MINUTE_2` | `30` | UTC minute of second daily run |
