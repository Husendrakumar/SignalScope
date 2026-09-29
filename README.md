# SignalScope: Automatic Radio Signal Analysis

SIH PS 147 — Understanding Unknown Radio Signals Automatically

## System Architecture

- **Frontend**: React + Vite UI running on `http://localhost:3000` (or `http://localhost:5173`)
- **Backend**: FastAPI API Server running on `http://localhost:8000`

## Running Development Environment

To run the application, open two terminal windows:

### Terminal 1 — Frontend (React / Vite)

```powershell
cd frontend
npm.cmd run dev
```

### Terminal 2 — Backend (FastAPI / Uvicorn)

```powershell
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

*(If `python` is unavailable on your system PATH, use `py -m uvicorn app.main:app --reload --port 8000`)*

## API Documentation

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/api/health](http://localhost:8000/api/health)
