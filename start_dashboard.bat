@echo off
echo ==========================================================
echo Starting Evolutionary Traffic Control System
echo ==========================================================

echo [1/3] Starting Genetic Algorithm Backend (Port 5000)...
start "GA Controller" cmd /k "cd backend && python main.py --mode ga --port 5000"

echo [2/3] Starting Fixed-Time Baseline Backend (Port 5001)...
start "Fixed Controller" cmd /k "cd backend && python main.py --mode fixed --port 5001"

echo [3/3] Starting Next.js Frontend Dashboard...
start "Frontend Dashboard" cmd /k "cd frontend\my-app && npm run dev"

echo All 3 services have been launched in separate terminal windows!
echo You can now close this launcher window.
