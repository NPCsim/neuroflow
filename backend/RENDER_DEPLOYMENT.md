# NeuroFlow Backend Deployment Guide: Render, Supabase & Neon

This guide covers how to deploy the NeuroFlow FastAPI backend to [Render](https://render.com) using Docker or Render's native Python runtime, and connect to a cloud PostgreSQL database on **Neon** or **Supabase**.

---

## 1. Architecture & Files Overview

| File | Location | Purpose |
| :--- | :--- | :--- |
| `Dockerfile` | `backend/Dockerfile` | Production container image using `python:3.11-slim`, non-root user, and dynamic `$PORT` handling. |
| `.dockerignore` | `backend/.dockerignore` | Excludes `.venv`, `.env`, local SQLite `.db` files, caches, and tests from container builds. |
| `start.sh` | `backend/start.sh` | POSIX entrypoint script that executes `alembic upgrade head` before launching `uvicorn`. |
| `render.yaml` | `render.yaml` & `backend/render.yaml` | Render Blueprint specification defining service specs, health checks, and environment variables. |
| `requirements.txt` | `backend/requirements.txt` | Backend dependencies including `psycopg2-binary>=2.9.9` for PostgreSQL connectivity. |
| `.env.example` | `backend/.env.example` | Complete environment variable template with documentation. |

---

## 2. Start Command Explained

```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

### Why this command is structured this way:
1. **`alembic upgrade head` runs first**:
   - Ensures the database tables (`tasks`, `goals`, `schedule_blocks`, `activity_log`, etc.) are fully up-to-date **before** the API server begins accepting traffic.
   - If a migration fails, the container/process exits with a non-zero code, preventing Render from routing traffic to an incompatible database schema.
2. **`uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`**:
   - `--host 0.0.0.0`: Required to bind to all network interfaces within the container/virtual machine.
   - `--port ${PORT:-8000}`: Render dynamically assigns a port via the `$PORT` environment variable (typically `10000`). Falling back to `8000` allows local testing.
3. **In `backend/start.sh`**:
   - Uses `exec uvicorn ...` so Uvicorn runs as PID 1, allowing it to receive standard OS termination signals (`SIGTERM`) from Render for zero-downtime rolling deploys.

---

## 3. Health Check (`/health`)

The backend exposes a health check endpoint at `/health` (`GET /health`):

```json
{
  "status": "ok",
  "app": "NeuroFlow API",
  "version": "1.0.0",
  "timestamp": "2026-10-26T20:30:00Z",
  "database": "connected"
}
```

- **Database Verification**: Executes `SELECT 1` against the configured database.
- **Status Codes**:
  - `200 OK`: Database connected, application healthy.
  - `503 Service Unavailable`: Database unreachable or connection failed.
- **Render Integration**: Set **Health Check Path** to `/health` in the Render dashboard or `render.yaml`. Render will ping this endpoint during deployment and only shift live traffic when it returns `200 OK`.

---

## 4. Environment Variables Reference

| Variable | Required | Description | Example |
| :--- | :---: | :--- | :--- |
| `DATABASE_URL` | **Yes** | PostgreSQL connection string formatted for SQLAlchemy. | `postgresql://user:pass@ep-cool-fog-123.us-east-2.aws.neon.tech/neondb?sslmode=require` |
| `GEMINI_API_KEY` | **Yes** | Google Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey). | `AIzaSy...` |
| `ALLOWED_ORIGINS` | **Yes** | Comma-separated list of origins allowed by CORS (aliases `CORS_ORIGINS`). | `https://your-frontend.vercel.app,http://localhost:3000` |
| `ENVIRONMENT` | No | Set to `production` on Render (`development` locally). | `production` |
| `LOG_LEVEL` | No | Application logging level (`INFO`, `DEBUG`, `WARNING`, `ERROR`). | `INFO` |
| `GEMINI_MODEL` | No | Model name for schedule optimization. Defaults to `gemini-3.8-flash`. | `gemini-3.8-flash` |

---

## 5. PostgreSQL Connection String Format for SQLAlchemy

NeuroFlow uses **synchronous SQLAlchemy 2.0** with the `psycopg2-binary` driver.

### Critical Rules:
1. **Driver Prefix**:
   - ✅ **Correct**: `postgresql://...` or `postgresql+psycopg2://...`
   - ❌ **Incorrect**: `postgresql+asyncpg://...` *(will fail: this codebase uses synchronous SQLAlchemy `Session`)*
   - ℹ️ **Legacy Prefix**: If you paste `postgres://...`, `backend/app/database.py` and `backend/alembic/env.py` automatically convert it to `postgresql://`.
2. **SSL Mode**:
   - Always append `?sslmode=require` for Neon and Supabase.
3. **Password URL Encoding**:
   - If your password contains special characters (`@`, `#`, `:`, `?`, `%`, `/`, `!`), you **must** URL-encode them:
     - `@` → `%40`
     - `#` → `%23`
     - `!` → `%21`
     - `%` → `%25`
     - `$` → `%24`
     - `&` → `%26`

---

## 6. Neon PostgreSQL Setup Instructions

### Step 1: Create a Neon Project
1. Log in to [Neon Console](https://console.neon.tech).
2. Click **Create Project**, choose a project name (e.g., `neuroflow-db`) and region closest to your Render service (e.g., `US East (Ohio)` or `US East (N. Virginia)`).
3. Click **Create Project**.

### Step 2: Retrieve the Connection String
1. On the Neon Dashboard, locate the **Connection Details** widget.
2. Select **Database**: `neondb`, **Role**: `neondb_owner`.
3. In the dropdown, choose **Pooled connection** (recommended for serverless scale) or **Direct connection**.
4. Check the **Parameters** toggle to ensure `sslmode=require` is included.
5. In the language dropdown, select **SQLAlchemy** or **Python**.

### Step 3: Verify the Format
Your connection string will look like this:
```text
postgresql://neondb_owner:npg_SECRET_PASS@ep-square-hill-a5xxxxxx-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require
```

---

## 7. Supabase PostgreSQL Setup Instructions

### Step 1: Create a Supabase Project
1. Log in to [Supabase Dashboard](https://supabase.com/dashboard).
2. Click **New project**, assign a name (e.g., `neuroflow`), choose an organization, and generate/save a strong database password.
3. Select a region matching your Render service (e.g., `East US (North Virginia)`).

### Step 2: Choose the Correct Supabase Connection String
Supabase provides two connection methods under **Project Settings** → **Database**:

#### Option A: Connection Pooler - Session Mode (Port 5432) — **RECOMMENDED**
- **Why**: Supabase's transaction pooler (port 6543) does not support prepared statements across sessions or certain DDL locks. Port 5432 (Session Mode) through Supavisor works for both **Alembic migrations** and **FastAPI requests**, and resolves IPv4 compatibility on Render!
- In Supabase: Navigate to **Project Settings** → **Database** → **Connection String** → Select **URI** tab → Select **Mode: Session** (Port `5432`).
- Format:
  ```text
  postgresql://postgres.your-project-ref:YOUR_PASSWORD@aws-0-us-east-1.pooler.supabase.com:5432/postgres?sslmode=require
  ```

#### Option B: Direct Connection (Port 5432)
- Direct host: `db.your-project-ref.supabase.co:5432`
- Note: Supabase direct connection requires IPv6 support. Since Render free tier outbound connections may prefer IPv4, **Option A (Supavisor pooler on port 5432)** is more reliable.

### Step 3: Encode Password Special Characters
If your Supabase password is `P@ss#word!`, replace:
- `@` with `%40`
- `#` with `%23`
- `!` with `%21`

Resulting connection string:
```text
postgresql://postgres.abcdefghijklmnop:P%40ss%23word%21@aws-0-us-east-1.pooler.supabase.com:5432/postgres?sslmode=require
```

---

## 8. Render Dashboard Step-by-Step Deployment

You can deploy using either the **Render Blueprint (Git-driven)** or the **Render Dashboard UI**.

### Method A: Deploy via Render Blueprint (`render.yaml`) — Fastest

1. Push your code with `render.yaml` to GitHub/GitLab.
2. In [Render Dashboard](https://dashboard.render.com), click **New +** → **Blueprint**.
3. Select your repository.
4. Render will parse `render.yaml` and show the `neuroflow-backend` service.
5. Enter the values for the synced variables:
   - `DATABASE_URL`: Your Supabase/Neon connection string.
   - `GEMINI_API_KEY`: Your Gemini API key.
   - `ALLOWED_ORIGINS`: Your frontend URL(s).
6. Click **Apply**. Render will build the Docker container, run migrations, and deploy.

---

### Method B: Deploy via Render Dashboard Manually

#### Step 1: Create Web Service
1. In [Render Dashboard](https://dashboard.render.com), click **New +** → **Web Service**.
2. Connect your Git repository.

#### Step 2: Configure Service Details

**Option 1: Using Docker (Recommended)**
- **Name**: `neuroflow-backend`
- **Region**: Choose the region closest to your database (e.g., `Oregon (US West)` or `Ohio (US East)`).
- **Branch**: `main` (or your active branch).
- **Root Directory**: `backend` (or leave blank if repository root is used).
- **Runtime**: `Docker`
- **Dockerfile Path**: `./Dockerfile` (if Root Directory is `backend`) or `./backend/Dockerfile` (if Root Directory is left blank).
- **Docker Context**: `.` (if Root Directory is `backend`) or `./backend` (if Root Directory is blank).
- **Instance Type**: `Free` or `Starter`.

**Option 2: Using Native Python Runtime**
- **Root Directory**: `backend`
- **Runtime**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`

#### Step 3: Set Health Check Path
1. Scroll down to **Advanced** settings.
2. Set **Health Check Path** to `/health`.

#### Step 4: Add Environment Variables
Under the **Environment Variables** section, add:

| Key | Value |
| :--- | :--- |
| `DATABASE_URL` | `postgresql://user:password@host/db?sslmode=require` |
| `GEMINI_API_KEY` | `AIzaSy...` |
| `ALLOWED_ORIGINS` | `https://your-frontend.vercel.app,http://localhost:3000` |
| `ENVIRONMENT` | `production` |
| `LOG_LEVEL` | `INFO` |
| `PYTHON_VERSION` | `3.11.9` *(required only if using native Python runtime)* |

#### Step 5: Deploy and Verify
1. Click **Create Web Service**.
2. Watch the deployment logs:
   - You should see:
     ```text
     ==> Running Alembic migrations...
     INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
     INFO  [alembic.runtime.migration] Will assume transactional DDL.
     INFO  [alembic.runtime.migration] Running upgrade -> 0b35cba51433, Initial schema
     INFO  [alembic.runtime.migration] Running upgrade 0b35cba51433 -> 1c46dba62544, Add rollover fields and activity_log table
     ==> Starting Uvicorn server on port 10000...
     INFO:     Started server process
     INFO:     Waiting for application startup.
     INFO:     Application startup complete.
     INFO:     Uvicorn running on http://0.0.0.0:10000 (Press CTRL+C to quit)
     ```
3. Test your live deployment:
   - Root URL: `https://neuroflow-backend.onrender.com/` → returns status `online`
   - Health check: `https://neuroflow-backend.onrender.com/health` → returns `{"status":"ok","database":"connected"}`
   - Interactive docs: `https://neuroflow-backend.onrender.com/docs`

---

## 9. Troubleshooting & FAQ

### Issue 1: `NoSuchModuleError: Can't load plugin: sqlalchemy.dialects:postgresql`
- **Cause**: Missing DBAPI driver for PostgreSQL.
- **Fix**: Ensure `psycopg2-binary>=2.9.9` is listed in `backend/requirements.txt`.

### Issue 2: `OperationalError: SSL connection has been closed unexpectedly`
- **Cause**: Serverless databases (Neon, Supabase) drop idle connections after inactivity.
- **Fix**: `backend/app/database.py` already includes `pool_pre_ping=True` and `pool_recycle=300` to automatically test and reconnect dropped connections.

### Issue 3: `alembic: command not found` or `start.sh: not found`
- **Cause**: Windows CRLF line endings in shell scripts.
- **Fix**: The Dockerfile automatically runs `sed -i 's/\r$//' start.sh` to ensure Unix LF line endings.

### Issue 4: Supabase Connection Timeout
- **Cause**: Direct Supabase connection (`db.[ref].supabase.co`) resolved to an IPv6 address that was not routable from the host.
- **Fix**: Use the Supabase **Connection Pooler (Session Mode on port 5432)** (`aws-0-[region].pooler.supabase.com:5432`), which supports IPv4 everywhere.
