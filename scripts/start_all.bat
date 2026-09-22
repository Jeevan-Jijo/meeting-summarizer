@echo off
echo Starting Meeting Intelligence System (Backend & Frontend)...
start "MIS Backend (FastAPI)" cmd /k "cd backend && call venv\Scripts\activate.bat && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
start "MIS Frontend (Next.js)" cmd /k "cd frontend && npm run dev"
echo Application launching...
echo Backend: http://127.0.0.1:8000/docs
echo Frontend: http://localhost:3000
