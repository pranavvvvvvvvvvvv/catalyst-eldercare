# Catalyst Eldercare

Starter workspace for the Catalyst Eldercare project.

## Project layout

- `backend/` contains the FastAPI application, configuration, schemas, services, database package, and tests.
- `frontend/` is reserved for the React + Vite application.

## Backend setup

From `backend/`, install dependencies and start the development server:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`; interactive documentation is at `/docs`.

