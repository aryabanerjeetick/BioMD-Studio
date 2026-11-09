@echo off
echo ===================================================
echo   Starting BioMD Studio - Online MD Platform
echo ===================================================

start "BioMD Backend" cmd /k "cd backend && ..\venv\Scripts\activate && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
timeout /t 3 /nobreak >nul
start "BioMD Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo BioMD Studio is starting!
echo Frontend: http://localhost:5173
echo Backend API: http://127.0.0.1:8000/docs
echo.
pause
