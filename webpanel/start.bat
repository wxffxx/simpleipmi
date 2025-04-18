@echo off
cd /d %~dp0

echo [1/3] Starting frontend...
start cmd /k "cd frontend && npm run dev"

echo [2/3] Starting backend...
start cmd /k "cd backend && python -m uvicorn main:app --reload"

echo [3/3] All started.
pause
