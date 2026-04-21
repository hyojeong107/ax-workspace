@echo off
set ROOT=C:\Users\user\Desktop\dev\ax-workspace\ax-workspace
start "FitStep API" cmd /k "cd /d "%ROOT%\08_FitStep_API" && "%ROOT%\venv\Scripts\uvicorn.exe" app.main:app --reload --port 8000"
start "FitStep Web" cmd /k "cd /d "%ROOT%\07_FitStep_Web" && "%ROOT%\venv\Scripts\streamlit.exe" run app.py"