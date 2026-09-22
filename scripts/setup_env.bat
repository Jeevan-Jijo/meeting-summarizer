@echo off
echo =========================================================
echo Setting up Meeting Intelligence System Python Environment
echo =========================================================

py -3.12 -m venv backend\venv
if errorlevel 1 (
    echo Failed to create venv with Python 3.12. Trying default python...
    python -m venv backend\venv
)

echo Installing backend dependencies...
call backend\venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r backend\requirements.txt

echo.
echo Installing frontend dependencies...
cd frontend
call npm install
cd ..

echo.
echo =========================================================
echo Setup complete! You can run start_all.bat to run the app.
echo =========================================================
pause
