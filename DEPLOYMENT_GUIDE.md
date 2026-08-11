# Comprehensive Run & Deployment Guide for Track4U

This guide provides step-by-step instructions to run, test, and deploy the **Track4U Multi-Tenant SaaS Task Manager & Website SSL Expiry Tracker** across three environments:
1. **Local Development (Python + Uvicorn)**
2. **Containerized Environment (Docker & Docker Compose)**
3. **Production Orchestration (Kubernetes - K8s)**

---

## 📋 Table of Contents
1. [Prerequisites Summary](#-prerequisites-summary)
2. [Environment Configuration (.env)](#-environment-configuration-env)
3. [Level 1: Running Locally (Local Python Environment)](#-level-1-running-locally-local-python-environment)
   - [1.1 Virtual Environment Setup](#11-virtual-environment-setup)
   - [1.2 Database Migrations](#12-database-migrations)
   - [1.3 Database Seeding](#13-database-seeding)
   - [1.4 Starting the FastAPI Server](#14-starting-the-fastapi-server)
   - [1.5 Accessing Application & API Docs](#15-accessing-application--api-docs)
   - [1.6 Executing Test Suite & Linters](#16-executing-test-suite--linters)
   - [1.7 Triggering Manual Expiry Checks](#17-triggering-manual-expiry-checks)
4. [Level 2: Running with Docker & Docker Compose](#-level-2-running-with-docker--docker-compose)
   - [2.1 Docker Prerequisites](#21-docker-prerequisites)
   - [2.2 Architecture of Docker Setup](#22-architecture-of-docker-setup)
   - [2.3 Building and Starting Containers](#23-building-and-starting-containers)
   - [2.4 Monitoring Container Logs & Health](#24-monitoring-container-logs--health)
   - [2.5 Triggering Expiry Checks in Docker](#25-triggering-expiry-checks-in-docker)
   - [2.6 Stopping & Volume Cleanup](#26-stopping--volume-cleanup)
5. [Level 3: Running on Kubernetes (K8s)](#-level-3-running-on-kubernetes-k8s)
   - [3.1 Prerequisites for Kubernetes](#31-prerequisites-for-kubernetes)
   - [3.2 K8s Architecture & Manifest Files](#32-k8s-architecture--manifest-files)
   - [3.3 Step-by-Step K8s Deployment](#33-step-by-step-k8s-deployment)
   - [3.4 Storage & SQLite Replica Locking Rule](#34-storage--sqlite-replica-locking-rule)
   - [3.5 Testing via Port Forwarding](#35-testing-via-port-forwarding)
   - [3.6 Automated & Manual CronJob Execution](#36-automated--manual-cronjob-execution)
   - [3.7 Teardown / Cleanup](#37-teardown--cleanup)
6. [PostgreSQL Production Migration Guide](#-postgresql-production-migration-guide)

---

## 🛠 Prerequisites Summary

| Component | Minimum Version | Required For |
|---|---|---|
| **Python** | 3.12+ | Local execution & testing |
| **pip / venv** | Latest | Package management |
| **Docker Engine** | 20.10+ | Containerized execution |
| **Docker Compose** | v2.0+ | Multi-container orchestration |
| **kubectl** | 1.28+ | Kubernetes deployment |
| **minikube / kind / k3s** | Optional | Local Kubernetes testing |

---

## ⚙️ Environment Configuration (.env)

The application uses **Pydantic Settings** to load environment variables. Create a `.env` file in the project root:

```bash
cp .env.example .env
```

### Key Environment Variables Explained:

```env
# General Settings
ENV=development
LOG_LEVEL=INFO

# Database Connection (SQLite async driver)
DATABASE_URL=sqlite+aiosqlite:///./data/app.db

# Authentication Security (JWT Secret Key - Change in Production!)
JWT_SECRET=super-secret-jwt-key-change-in-production-123456789
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Internal Service Secret (Protects /api/v1/internal/run-expiry-checks)
INTERNAL_API_TOKEN=internal-secret-token-change-in-production

# Website & SSL Expiry Monitoring Threshold (in Days)
ALERT_THRESHOLD_DAYS=30

# CORS Allowed Origins (JSON Array or String)
CORS_ORIGINS=["http://localhost:8000", "http://127.0.0.1:8000"]

# SMTP Email Alert Settings (Optional for Real Email Sending)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=alerts@example.com
SMTP_PASSWORD=your-app-password
ALERT_FROM_EMAIL=alerts@example.com
```

---

## 🐍 Level 1: Running Locally (Local Python Environment)

### 1.1 Virtual Environment Setup

From the project directory (`task-manager/`), create and activate a Python 3.12 virtual environment:

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment (Linux/macOS)
source .venv/bin/activate

# Upgrade pip and install all project dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

### 1.2 Database Migrations

Run **Alembic** migrations to create SQLite tables and indices:

```bash
PYTHONPATH=. alembic upgrade head
```

This creates the database tables under `./data/app.db`.

---

### 1.3 Database Seeding

Populate the database with initial demo data (organizations, projects, tasks, comments, and tracked websites):

```bash
PYTHONPATH=. python scripts/seed.py
```

#### Demo Account Credentials:
- **Email**: `demo@example.com`
- **Password**: `DemoPassword123!`
- **Organization**: `Acme Corporation` (`pro` plan)

---

### 1.4 Starting the FastAPI Server

Start the application with Uvicorn:

```bash
PYTHONPATH=. uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

### 1.5 Accessing Application & API Docs

Once the server is running, access the web application in your browser:

- **Web Frontend (UI)**: `http://localhost:8000`
- **Interactive OpenAPI (Swagger) Docs**: `http://localhost:8000/docs`
- **ReDoc Documentation**: `http://localhost:8000/redoc`
- **Health Check Endpoint**: `http://localhost:8000/health`

---

### 1.6 Executing Test Suite & Linters

Run the automated Pytest suite with zero network calls (mocked SSL/WHOIS):

```bash
# Run tests
PYTHONPATH=. pytest -v

# Run code formatters and linters
ruff check app tests
black --check app tests
```

---

### 1.7 Triggering Manual Expiry Checks

To simulate background domain and SSL expiry checks locally:

```bash
curl -X POST http://localhost:8000/api/v1/internal/run-expiry-checks \
  -H "X-Internal-Token: internal-secret-token-change-in-production"
```

---

## 🐳 Level 2: Running with Docker & Docker Compose

### 2.1 Docker Prerequisites
Ensure **Docker Engine** and **Docker Compose** are installed and running.

---

### 2.2 Architecture of Docker Setup

- **`Dockerfile`**: Multi-stage build using `python:3.12-slim` for small image size and non-root execution (`appuser`).
- **`docker-entrypoint.sh`**: Automatically runs `alembic upgrade head` on container startup before initiating Gunicorn.
- **`docker-compose.yml`**: Defines the `api` service with persistent volume (`sqlite_data`) mounted at `/app/data`.
- **`docker-compose.override.yml`**: Enables local source code mounting and Uvicorn `--reload` hot reloading.

---

### 2.3 Building and Starting Containers

To build the image and run the stack in background mode:

```bash
# Build and start container
docker compose up --build -d
```

---

### 2.4 Monitoring Container Logs & Health

Check the status of running containers:

```bash
# View container status
docker compose ps

# View real-time logs
docker compose logs -f api
```

The Dockerfile includes an automated `HEALTHCHECK` that queries `http://localhost:8000/health` every 30 seconds.

---

### 2.5 Triggering Expiry Checks in Docker

Run the internal check endpoint against the running container:

```bash
curl -X POST http://localhost:8000/api/v1/internal/run-expiry-checks \
  -H "X-Internal-Token: internal-secret-token-change-in-production"
```

---

### 2.6 Stopping & Volume Cleanup

```bash
# Stop containers
docker compose down

# Stop containers AND delete persistent database volumes
docker compose down -v
```

---

## ☸️ Level 3: Running on Kubernetes (K8s)

### 3.1 Prerequisites for Kubernetes
- Accessible K8s cluster (`minikube`, `kind`, `k3s`, EKS, GKE, AKS, etc.)
- Installed and configured `kubectl` CLI tool.

---

### 3.2 K8s Architecture & Manifest Files

All Kubernetes configuration files are stored in the `k8s/` directory:

| File Name | Resource Type | Description |
|---|---|---|
| `k8s/namespace.yaml` | `Namespace` | Creates isolated namespace `task-manager` |
| `k8s/configmap.yaml` | `ConfigMap` | Non-sensitive settings (`ENV`, `ALERT_THRESHOLD_DAYS`, `SMTP_HOST`) |
| `k8s/secret.yaml` | `Secret` | Sensitive keys (`JWT_SECRET`, `INTERNAL_API_TOKEN`, `SMTP_PASSWORD`) |
| `k8s/pvc.yaml` | `PersistentVolumeClaim` | 5GB `ReadWriteOnce` storage for SQLite database file |
| `k8s/deployment.yaml` | `Deployment` | Single replica (`replicas: 1`) API deployment with health probes |
| `k8s/service.yaml` | `Service` | `ClusterIP` exposing port 80 -> 8000 |
| `k8s/ingress.yaml` | `Ingress` | NGINX ingress routing rule for domain access |
| `k8s/cronjob.yaml` | `CronJob` | Automated daily job (`0 6 * * *`) hitting expiry check endpoint |

---

### 3.3 Step-by-Step K8s Deployment

Deploy resources in sequential order:

```bash
# 1. Create Namespace
kubectl apply -f k8s/namespace.yaml

# 2. Create Configuration & Secrets
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml

# 3. Create Persistent Volume Claim
kubectl apply -f k8s/pvc.yaml

# 4. Deploy Application & Cluster Service
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# 5. Deploy Ingress Controller Rule
kubectl apply -f k8s/ingress.yaml

# 6. Deploy Daily Expiry Check CronJob
kubectl apply -f k8s/cronjob.yaml
```

---

### 3.4 Storage & SQLite Replica Locking Rule

> [!IMPORTANT]
> **Single Replica Limitation (`replicas: 1`)**:
> SQLite is a file-based database that relies on file system locking for ACID compliance. Running multiple pod replicas pointing to the same SQLite database file will lead to database locks and data corruption.
> **Do not attach a HorizontalPodAutoscaler (HPA)** to `task-manager-api` while using SQLite.

---

### 3.5 Testing via Port Forwarding

If you do not have an Ingress controller configured, test the application directly using `kubectl port-forward`:

```bash
# Port-forward K8s service to local port 8000
kubectl port-forward svc/task-manager-api 8000:80 -n task-manager
```

Now open `http://localhost:8000` in your browser.

---

### 3.6 Automated & Manual CronJob Execution

The Kubernetes CronJob runs automatically every day at 06:00 UTC (`schedule: "0 6 * * *"`).

To trigger an instant execution of the CronJob on-demand:

```bash
# Manually trigger job execution from CronJob spec
kubectl create job --from=cronjob/website-expiry-checker manual-expiry-run-01 -n task-manager

# Check logs of triggered job
kubectl logs job/manual-expiry-run-01 -n task-manager
```

---

### 3.7 Teardown / Cleanup

To delete all deployed resources from your Kubernetes cluster:

```bash
kubectl delete -f k8s/
```

Or delete the entire namespace:

```bash
kubectl delete namespace task-manager
```

---

## 🐘 PostgreSQL Production Migration Guide

To scale the application horizontally (`replicas: 3+` with HPA in Kubernetes):

1. **Install `asyncpg` dependency**:
   Add `asyncpg>=0.29.0` to `requirements.txt`.

2. **Update Database URL in `.env` or K8s Secret**:
   ```env
   DATABASE_URL=postgresql+asyncpg://db_user:db_password@postgres-host:5432/task_manager_db
   ```

3. **Scale Deployment Replicas**:
   In `k8s/deployment.yaml`, update `replicas: 1` to `replicas: 3`.

4. **Run Migrations**:
   Alembic will automatically execute standard SQL statements against PostgreSQL without code changes.
