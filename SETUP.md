# 🚀 Track4U — Complete Setup Guide

> **Full-stack SaaS Task Manager + Domain/SSL Expiry Tracker + Custom Reminders**
> Built with FastAPI · SQLite · Jinja2/HTMX · APScheduler

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Project Structure](#project-structure)
3. [Quick Start](#quick-start)
4. [Environment Variables Reference](#environment-variables-reference)
5. [Gmail App Password Setup](#gmail-app-password-setup)
6. [Running Migrations](#running-migrations)
7. [Starting the Server](#starting-the-server)
8. [Features Overview](#features-overview)
9. [Email Alert System](#email-alert-system)
10. [Custom Reminders](#custom-reminders)
11. [Manual Trigger API](#manual-trigger-api)
12. [Testing Email Alerts](#testing-email-alerts)
13. [Troubleshooting](#troubleshooting)

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.10+ |
| pip | Latest |
| Git | Any |

No Docker required for local development.

---

## Project Structure

```
task-manager/
├── .env                        # ← Your credentials (never commit!)
├── .env.example                # Reference template
├── requirements.txt            # Python dependencies
├── alembic.ini                 # Database migration config
├── app/
│   ├── main.py                 # App entry point + scheduler startup
│   ├── core/
│   │   ├── config.py           # All settings (reads from .env)
│   │   ├── deps.py             # FastAPI dependency injection
│   │   └── security.py         # JWT + password hashing
│   ├── models/
│   │   ├── user.py             # User model
│   │   ├── org.py              # Organization + OrgMember
│   │   ├── project.py          # Project model
│   │   ├── task.py             # Task, Comment, Label, ActivityLog
│   │   ├── website.py          # TrackedWebsite + ExpiryAlertLog
│   │   └── reminder.py         # CustomReminder + ReminderAlertLog (NEW)
│   ├── schemas/                # Pydantic request/response models
│   ├── api/v1/
│   │   ├── auth.py             # Signup, Login, Logout, /me
│   │   ├── orgs.py             # Organization management
│   │   ├── projects.py         # Project CRUD
│   │   ├── tasks.py            # Task CRUD + comments
│   │   ├── websites.py         # Tracked website CRUD + check-now
│   │   ├── reminders.py        # Custom reminder CRUD (NEW)
│   │   └── internal.py         # Scheduler trigger endpoints
│   ├── services/
│   │   ├── email.py            # SMTP email sender (with HTML support)
│   │   ├── website_check.py    # SSL + WHOIS checks + alert logic
│   │   ├── reminder_check.py   # Custom reminder alert logic (NEW)
│   │   └── scheduler.py        # APScheduler 2×/day cron setup (NEW)
│   ├── templates/              # Jinja2 HTML templates
│   │   ├── base.html
│   │   ├── auth/
│   │   ├── projects/
│   │   ├── tasks/
│   │   ├── websites/
│   │   └── reminders/          # (NEW)
│   └── web/router.py           # Web page routes (SSR)
├── alembic/versions/
│   ├── 001_initial_schema.py   # Base schema
│   └── 002_custom_reminders.py # Custom reminders tables (NEW)
└── data/
    └── app.db                  # SQLite database file (auto-created)
```

---

## Quick Start

```bash
# 1. Clone and enter the project
cd track4U-1/task-manager

# 2. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
nano .env                        # Fill in your SMTP credentials (see below)

# 5. Run database migrations
alembic upgrade head

# 6. Start the development server
uvicorn app.main:app --reload --port 8000

# 7. Open the app
# Browser: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

---

## Environment Variables Reference

Open `.env` and configure all values:

| Variable | Default | Description |
|----------|---------|-------------|
| `ENV` | `development` | `development` or `production` |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/app.db` | Database URL |
| `JWT_SECRET` | (change this!) | Secret key for JWT token signing |
| `JWT_EXPIRE_MINUTES` | `1440` | Token validity (1440 = 24 hours) |
| `SMTP_HOST` | `smtp.gmail.com` | SMTP server hostname |
| `SMTP_PORT` | `587` | 587 = STARTTLS, 465 = SSL |
| `SMTP_USER` | **(REQUIRED)** | Your Gmail address |
| `SMTP_PASSWORD` | **(REQUIRED)** | Gmail App Password (16 chars) |
| `ALERT_FROM_EMAIL` | Same as `SMTP_USER` | The "From" address in emails |
| `ALERT_THRESHOLD_DAYS` | `30` | Alert when expiry is within N days |
| `EMAIL_ALERT_DEDUP_HOURS` | `11` | Skip re-send within N hours (allows 2×/day) |
| `SCHEDULER_HOUR_1` | `2` | UTC hour for morning run (2 = 7:30 AM IST) |
| `SCHEDULER_MINUTE_1` | `30` | UTC minute for morning run |
| `SCHEDULER_HOUR_2` | `14` | UTC hour for evening run (14 = 7:30 PM IST) |
| `SCHEDULER_MINUTE_2` | `30` | UTC minute for evening run |
| `INTERNAL_API_TOKEN` | (change this!) | Token for manual trigger API |

> [!IMPORTANT]
> **Always change `JWT_SECRET` and `INTERNAL_API_TOKEN` before deploying to production!**
> Generate secure values with:
> ```bash
> python -c "import secrets; print(secrets.token_hex(32))"
> ```

---

## Gmail App Password Setup

> [!NOTE]
> Gmail requires an **App Password** (not your account password) for SMTP access.
> Your regular Gmail password will NOT work.

**Step-by-step:**

1. Go to your Google Account: https://myaccount.google.com
2. Click **Security** in the left sidebar
3. Under "How you sign in to Google", enable **2-Step Verification** (required)
4. Go back to Security → search for **App passwords**
5. Click **App passwords**
6. Select app: **Mail** | Select device: **Other** → type "Track4U"
7. Click **Generate**
8. Copy the **16-character password** (e.g. `abcd efgh ijkl mnop`)
9. In your `.env`:
   ```
   SMTP_USER=yourname@gmail.com
   SMTP_PASSWORD=abcdefghijklmnop    # No spaces
   ALERT_FROM_EMAIL=yourname@gmail.com
   ```

---

## Running Migrations

The project uses **Alembic** for database schema management.

```bash
# Apply all pending migrations (run this every time you pull new code)
alembic upgrade head

# Check current migration state
alembic current

# See migration history
alembic history --verbose

# Roll back one migration (if needed)
alembic downgrade -1
```

**Migration files:**
- `001_initial_schema.py` — All base tables (users, orgs, projects, tasks, websites, etc.)
- `002_custom_reminders.py` — Custom reminders + reminder alert logs

> [!WARNING]
> If you have an existing database from a previous version, always run `alembic upgrade head` before starting the server to apply new migrations.

---

## Starting the Server

### Development (with auto-reload)
```bash
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

### Production (with Gunicorn)
```bash
source .venv/bin/activate
gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  -w 1 \
  -b 0.0.0.0:8000 \
  --timeout 120
```

> [!IMPORTANT]
> Use **1 worker** (`-w 1`) when running with the built-in scheduler to avoid duplicate scheduled jobs. If you need multiple workers, use an external scheduler (see `DEPLOYMENT_GUIDE.md`).

### Verify startup output
When the server starts correctly, you'll see:
```
🚀 Track4U starting up...
Added job "Morning Expiry & Reminder Check (8AM IST)" to job store "default"
Added job "Evening Expiry & Reminder Check (8PM IST)" to job store "default"
🕐 Scheduler started with 2 daily jobs:
   Run 1: 02:30 UTC
   Run 2: 14:30 UTC
✅ Background scheduler active.
Application startup complete.
```

---

## Features Overview

### 1. Multi-Tenant Authentication
- Sign up creates a user + personal organization automatically
- JWT-based auth stored in httpOnly cookies
- Switch organizations via `X-Org-Id` header or `active_org_id` cookie

### 2. Project & Task Management
- Create projects, assign tasks with priority, status, due dates
- Kanban board view (To Do / In Progress / Done)
- Task comments + activity log
- Label/tag system

### 3. 🌐 Website & SSL Expiry Tracker
- Add any domain URL — immediately checks SSL cert + WHOIS domain expiry
- Background checks run **2× daily** (8 AM + 8 PM IST)
- Email alerts when within `ALERT_THRESHOLD_DAYS` (default: 30 days)
- **Auto-stops emailing when domain/SSL is renewed** (beyond threshold)
- Manual re-check button available per site
- Alert log history per website

### 4. 🔔 Custom Reminders
- Set any date as a target + how many days before to start alerting
- Perfect for: password expiry, license renewals, subscription payments, etc.
- Email alerts sent **2× daily** during the alert window
- Pause/resume individual reminders without deleting
- Repeating reminders supported via `repeat_interval_days`

### 5. ✉️ Smart Email System
- Beautiful HTML emails with dark theme
- Urgency color coding: 🟢 Notice → 🟡 Warning → 🔴 Critical
- De-duplication: never sends the same alert within 11 hours
- Stub mode: if SMTP not configured, prints to logs instead (safe for dev)

---

## Email Alert System

### How 2× Daily Emails Work

```
Scheduler triggers → 8:00 AM IST (02:30 UTC)
  ↓
For each tracked website:
  - Run SSL check + WHOIS lookup
  - If expiry_date > threshold days → SKIP (renewed, auto-stop)
  - If expiry_date <= threshold days:
    - Check if alert was sent in last 11 hours
    - If yes → SKIP (de-duplication)
    - If no → SEND EMAIL + log it

Scheduler triggers → 8:00 PM IST (14:30 UTC)
  ↓ (Same process repeats)
```

### De-duplication Logic
- `EMAIL_ALERT_DEDUP_HOURS=11` means: between the 8AM and 8PM runs (12h apart), each alert fires once per run (11h window < 12h gap).
- If you want **1×/day**: set `EMAIL_ALERT_DEDUP_HOURS=23`
- If you want **no limit**: set `EMAIL_ALERT_DEDUP_HOURS=0`

### Auto-Stop on Renewal
When a domain or SSL certificate is renewed (expiry pushed beyond threshold):
1. No alert email is sent
2. Stale alert logs older than 30 days are cleaned up automatically
3. Alerts resume if expiry falls back within threshold

---

## Custom Reminders

### Creating a Reminder (Web UI)
1. Go to **🔔 Reminders** in the navigation
2. Click **"+ New Reminder"**
3. Fill in:
   - **Title**: e.g. "Gmail Password Expiry"
   - **Target Date**: When the thing expires/happens
   - **Alert from (days before)**: Start alerting N days before target date
4. Click **Create Reminder**

### Example Use Cases

| Reminder | Target Date | Alert From |
|----------|-------------|------------|
| Gmail password expires | Jan 30 | 25 days before (→ alerts start Jan 5) |
| Domain renewal due | Mar 15 | 30 days before |
| SSL cert expires | Apr 1 | 14 days before |
| Server license renewal | Dec 31 | 60 days before |
| Subscription payment | Monthly | 5 days before |

### Via API
```bash
curl -X POST http://localhost:8000/api/v1/reminders \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=<your-token>" \
  -d '{
    "title": "Gmail Password Expiry",
    "description": "Reset password at myaccount.google.com",
    "target_date": "2026-02-28",
    "remind_days_before": 25
  }'
```

---

## Manual Trigger API

Trigger checks manually without waiting for the scheduler:

```bash
# Run website expiry checks now
curl -X POST http://localhost:8000/api/v1/internal/run-expiry-checks \
  -H "X-Internal-Token: your-internal-token-from-env"

# Run reminder checks now
curl -X POST http://localhost:8000/api/v1/internal/run-reminder-checks \
  -H "X-Internal-Token: your-internal-token-from-env"

# Run BOTH at once (same as scheduler does)
curl -X POST http://localhost:8000/api/v1/internal/run-all-checks \
  -H "X-Internal-Token: your-internal-token-from-env"
```

Replace `your-internal-token-from-env` with your `INTERNAL_API_TOKEN` from `.env`.

---

## Testing Email Alerts

### Step 1: Verify SMTP configuration
```bash
curl http://localhost:8000/health
# Should show: "smtp_configured": true
```

### Step 2: Add a test website
1. Log in at http://localhost:8000
2. Go to **🌐 Website Expiry Tracker**
3. Add a domain like `https://example.com`
4. Click the site → it will check immediately

### Step 3: Test reminder email
Create a reminder with:
- Target date = **today** (or tomorrow)
- Alert from = **10 days before**
Then trigger manually:
```bash
curl -X POST http://localhost:8000/api/v1/internal/run-reminder-checks \
  -H "X-Internal-Token: $(grep INTERNAL_API_TOKEN .env | cut -d= -f2)"
```

### Step 4: Check logs
```bash
# You'll see either:
✅ Email sent to you@gmail.com | Subject: [Track4U] Reminder: ...
# or (if SMTP not configured):
[STUB EMAIL — configure SMTP_USER in .env to send real mail]
```

---

## Troubleshooting

### "stub email" appearing in logs
→ `SMTP_USER` is empty in `.env`. Fill it in and restart the server.

### 535 Authentication Failed
→ You're using your Gmail password instead of an **App Password**.
→ See [Gmail App Password Setup](#gmail-app-password-setup).

### "Application startup failed" / ImportError
```bash
# Check for missing packages
pip install -r requirements.txt
# Check for Python version
python --version  # Must be 3.10+
```

### Alembic error: "Table already exists"
```bash
# Reset and reapply
alembic downgrade base
alembic upgrade head
# Or delete the database and start fresh:
rm data/app.db && alembic upgrade head
```

### Scheduler fires but no email
1. Check logs for `❌ Failed to send email`
2. Verify SMTP credentials in `.env`
3. Check recipient's user has `notify_on_expiry = true` in Settings
4. Check de-dup: was an email already sent in the last 11 hours?

### Port already in use
```bash
# Use a different port
uvicorn app.main:app --reload --port 8001
```
