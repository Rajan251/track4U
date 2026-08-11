# Track4U — Open Source SaaS Task Manager & Expiry Tracker

<p align="center">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="MIT License">
  <img src="https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/SQLite-aiosqlite-003B57?logo=sqlite&logoColor=white" alt="SQLite">
  <img src="https://img.shields.io/badge/Docker-Supported-2496ED?logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/UI-HTMX%20%2B%20TailwindCSS-38BDF8" alt="HTMX + Tailwind">
</p>

**Track4U** is a lightweight, production-ready, open-source multi-tenant SaaS platform that combines **Task & Project Kanban Management**, **Domain & SSL Expiry Monitoring**, and **Custom Date Reminders** with automated multi-channel email alerts.

---

## 🌟 Key Features

### 📋 Interactive Task & Project Kanban
* **Kanban Task Board**: Group tasks by status (`To Do`, `In Progress`, `Done`) with real-time status dropdown transitions.
* **Full In-Place Task Management**: Create, edit title/description/priority/due date, or delete tasks directly from Kanban cards or task detail pages.
* **Task Alert Notifications**: Assign optional custom alert email lists per task (`person1@domain.com, person2@domain.com`).
* **Status Change Alerts**: Automated HTML email notifications sent instantly whenever a task status transitions between columns.
* **Activity Log & Discussions**: Rich task comments and detailed audit trails.

### 🌐 Domain & SSL Expiry Tracker
* **Real-time Certificate & WHOIS Checks**: Monitors both SSL certificate expiration dates and WHOIS domain expiration dates.
* **Automated Daily Background Audits**: 2× daily scheduled checks (configurable cron timing).
* **Renewal Auto-Stop**: Automatically stops alert dispatches once a domain or SSL certificate has been renewed.
* **Manual Inspection**: Instant "Check Now" trigger per tracked domain.

### 🔔 Custom Reminders Module
* **Target Date Monitoring**: Track license renewals, subscription due dates, or recurring deadlines.
* **Configurable Warning Window**: Set warning thresholds (e.g. start alerting 7 days before due date).
* **Pause / Resume**: Toggle monitoring active state without deleting reminder records.

### ✉️ Multi-Recipient Smart Alerting System
* **Curated Dark-Mode HTML Templates**: Color-coded urgency indicators (🟢 Upcoming, 🟡 Warning, 🔴 Critical/Overdue).
* **Flexible Recipients**: Send alerts to task assignees, custom manual email inputs, or global ops team distribution lists (`ALERT_TO_EMAILS`).
* **De-Duplication Engine**: Configurable de-duplication window prevents alert spamming.

---

## 🏗 System Architecture

```text
               ┌──────────────────────────────────────────────┐
               │    Frontend UI (TailwindCSS + Jinja2/HTMX)   │
               └──────────────────────┬───────────────────────┘
                                      │ HTTP / REST
               ┌──────────────────────▼───────────────────────┐
               │           FastAPI Backend Services           │
               │  ┌───────────────┬────────────────────────┐  │
               │  │ REST APIs     │ APScheduler Background │  │
               │  │ (/api/v1/*)   │ (2x Daily Cron Jobs)   │  │
               │  └───────────────┴────────────────────────┘  │
               └──────────────────────┬───────────────────────┘
                                      │ SQLAlchemy 2.0 Async
               ┌──────────────────────▼───────────────────────┐
               │  SQLite Database (Persistent Docker Volume)   │
               └──────────────────────────────────────────────┘
```

---

## 🚀 Quickstart Guide

### Option 1: Run with Docker Compose (Recommended)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/track4u.git
   cd track4u/task-manager
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env to set your JWT_SECRET and SMTP credentials if sending real emails
   ```

3. **Launch containerized stack:**
   ```bash
   docker compose up -d --build
   ```

4. **Access the application:**
   - Web Dashboard: `http://localhost:8000`
   - Interactive Swagger API Documentation: `http://localhost:8000/docs`
   - System Health Check: `http://localhost:8000/health`

---

### Option 2: Local Development Setup (Without Docker)

1. **Create and activate Python virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize environment settings:**
   ```bash
   cp .env.example .env
   ```

4. **Execute database migrations:**
   ```bash
   alembic upgrade head
   ```

5. **Start Uvicorn server:**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

---

## ⚙️ Environment Variables Reference

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `ENV` | `development` | Environment mode (`development`, `production`, `testing`) |
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `CORS_ORIGINS` | `["http://localhost:8000"]` | Allowed CORS origins (JSON array or comma-separated) |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/app.db` | SQLAlchemy database connection string |
| `JWT_SECRET` | *(Random 32-char string)* | Secret key for JWT signature validation |
| `JWT_EXPIRE_MINUTES` | `1440` | JWT token validity window in minutes (1440 = 24 hours) |
| `SMTP_HOST` | `smtp.gmail.com` | SMTP host server address |
| `SMTP_PORT` | `587` | SMTP port (587 for TLS, 465 for SSL) |
| `SMTP_USER` | `""` | SMTP authentication username / email |
| `SMTP_PASSWORD` | `""` | SMTP authentication app-specific password |
| `ALERT_FROM_EMAIL` | `""` | Sender email address displayed in outgoing alerts |
| `ALERT_TO_EMAILS` | `""` | Optional comma-separated global recipient list |
| `ALERT_THRESHOLD_DAYS` | `30` | Default warning window threshold in days |
| `EMAIL_ALERT_DEDUP_HOURS` | `11` | Hours to wait before re-sending identical alerts |
| `SCHEDULER_HOUR_1` | `2` | First daily background check hour (UTC) |
| `SCHEDULER_MINUTE_1` | `30` | First daily background check minute (UTC) |
| `SCHEDULER_HOUR_2` | `14` | Second daily background check hour (UTC) |
| `SCHEDULER_MINUTE_2` | `30` | Second daily background check minute (UTC) |
| `INTERNAL_API_TOKEN` | *(Random secret token)* | Header token for protected internal trigger endpoints |

---

## 💾 Data Persistence & Backup Workflow

Database state persists inside a Docker named volume (`sqlite_data`) mapped to `/app/data/`. Rebuilding or restarting Docker containers **will not** erase application data.

### Database Snapshot & Restoration CLI Script

A production backup/restore CLI tool is provided in `scripts/backup-db.sh`:

```bash
# Make script executable
chmod +x scripts/backup-db.sh

# Create an instant timestamped snapshot
./scripts/backup-db.sh backup

# List existing backups
./scripts/backup-db.sh list

# Restore database from the latest snapshot
./scripts/backup-db.sh restore

# Restore database from a specific snapshot file
./scripts/backup-db.sh restore ./data/app_20260811_120000.db
```

---

## 🔌 API Endpoints Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/auth/signup` | Create user account & organization |
| `POST` | `/api/v1/auth/login` | Authenticate user & obtain JWT cookie |
| `GET` / `POST` | `/api/v1/projects` | List projects or create new project |
| `PATCH` / `DELETE` | `/api/v1/projects/{id}` | Update project metadata or delete project |
| `GET` / `POST` | `/api/v1/tasks` | List tasks or create new task |
| `PATCH` / `DELETE` | `/api/v1/tasks/{id}` | Update task status/priority/alert_emails or delete task |
| `GET` / `POST` | `/api/v1/websites` | List monitored websites or register domain |
| `PATCH` / `DELETE` | `/api/v1/websites/{id}` | Update website label/status or delete website |
| `POST` | `/api/v1/websites/{id}/check-now` | Trigger immediate SSL/domain check |
| `GET` / `POST` | `/api/v1/reminders` | List reminders or create new reminder |
| `PATCH` / `DELETE` | `/api/v1/reminders/{id}` | Update reminder parameters or delete reminder |
| `POST` | `/api/v1/internal/run-all-checks` | Trigger full background audit on demand |
| `GET` | `/health` | Application status & health metrics |

---

## 🤝 Contributing

Contributions are welcome! Please review [CONTRIBUTING.md](CONTRIBUTING.md) for details on code style, testing guidelines, and submission workflow.

---

## 📄 License

This project is open-source and licensed under the [MIT License](LICENSE).
