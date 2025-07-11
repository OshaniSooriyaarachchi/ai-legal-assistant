@echo off
echo Starting AI Legal Assistant Backend...

cd /d "d:\Users\USER\Documents\Capricon\ai-legal-assistant\ai-legal-assistant-backend"

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing Python dependencies...
pip install -r requirements.txt

echo Starting backend server on http://localhost:8000...
uvicorn main:app --reload --host 127.0.0.1 --port 8000

pause
