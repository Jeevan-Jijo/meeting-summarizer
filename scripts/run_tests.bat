@echo off
echo Running MIS Backend Unit and Integration Tests...
cd backend
call venv\Scripts\activate.bat
pytest -v
cd ..
