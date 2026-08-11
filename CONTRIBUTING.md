# Contributing to Track4U 🚀

Thank you for your interest in contributing to **Track4U**! We welcome bug reports, feature suggestions, documentation improvements, and code contributions from the open-source community.

---

## 🛠️ Local Development Setup

### Prerequisites
- Python 3.10+
- Docker & Docker Compose (optional, for containerized dev)
- Git

### 1. Fork & Clone Repository
```bash
git clone https://github.com/your-username/track4u.git
cd track4u/task-manager
```

### 2. Create Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Setup Environment Variables
```bash
cp .env.example .env
```
Edit `.env` to configure your local database path and optional SMTP parameters.

### 4. Run Database Migrations
```bash
alembic upgrade head
```

### 5. Start Development Server
```bash
uvicorn app.main:app --reload --port 8000
```
Visit `http://localhost:8000` in your browser. API Swagger documentation is available at `http://localhost:8000/docs`.

---

## 🧪 Running Tests & Linting

### Run Unit Tests
```bash
pytest
```

### Code Formatting & Linting
We use **Ruff** for linting and code formatting:
```bash
ruff check .
ruff format .
```

---

## 📂 Project Architecture

```text
task-manager/
├── alembic/              # Database migration scripts
├── app/
│   ├── api/v1/          # RESTful FastAPI endpoints
│   ├── core/            # Config, security, dependencies
│   ├── db/              # Database session & base models
│   ├── models/          # SQLAlchemy models (Tasks, Projects, Websites, Reminders)
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Expiry checks, reminders, scheduler, email dispatcher
│   ├── templates/       # Jinja2 & HTMX UI views
│   └── main.py          # FastAPI application entrypoint
├── data/                # SQLite persistent storage directory
├── scripts/             # Backup/restore utility scripts
├── docker-compose.yml   # Docker Compose setup
├── Dockerfile           # Multi-stage Docker image definition
└── requirements.txt     # Python dependencies
```

---

## 📥 Submitting a Pull Request (PR)

1. Create a descriptive branch:
   ```bash
   git checkout -b feature/add-new-alert-channel
   ```
2. Make your changes and commit with clear messages:
   ```bash
   git commit -m "feat(alerts): add webhook alert channel"
   ```
3. Push to your fork:
   ```bash
   git push origin feature/add-new-alert-channel
   ```
4. Open a **Pull Request** against the `main` branch with a summary of changes and testing steps.

---

## 📄 License
By contributing to Track4U, you agree that your contributions will be licensed under the project's [MIT License](LICENSE).
